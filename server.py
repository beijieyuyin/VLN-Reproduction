from fastapi import FastAPI, HTTPException
import uvicorn
import cv2
import numpy as np
import base64
import json
import torch
import os
import imageio
import time
import argparse



from uninavid.mm_utils import get_model_name_from_path
from uninavid.model.builder import load_pretrained_model
from uninavid.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN
from uninavid.conversation import conv_templates, SeparatorStyle
from uninavid.mm_utils import tokenizer_image_token, KeywordsStoppingCriteria

app = FastAPI()

class UniNaVid_Agent():
    def __init__(self, model_path):
        print("Initialize UniNaVid")
        self.conv_mode = "vicuna_v1"
        self.model_name = get_model_name_from_path(model_path)
        self.tokenizer, self.model, self.image_processor, self.context_len = load_pretrained_model(
            model_path, None, self.model_name
        )
        assert self.image_processor is not None
        print("Initialization Complete")
        
        self.promt_template = "Imagine you are a robot programmed for navigation tasks. You have been given a video of historical observations and an image of the current observation <image>. Your assigned task is: '{}'. Analyze this series of images to determine your next four actions. The predicted action should be one of the following: forward, left, right, or stop."
        self.rgb_list = []
        self.count_id = 0
        self.reset()

    def process_images(self, rgb_list):
        batch_image = np.asarray(rgb_list)
        self.model.get_model().new_frames = len(rgb_list)
        video = self.image_processor.preprocess(batch_image, return_tensors='pt')['pixel_values'].half().cuda()
        return [video]

    def predict_inference(self, prompt):
       
        question = prompt.replace(DEFAULT_IMAGE_TOKEN, '').replace('\n', '')
        qs = prompt

        VIDEO_START_SPECIAL_TOKEN = "<video_special>"
        VIDEO_END_SPECIAL_TOKEN = "</video_special>"
        IMAGE_START_TOKEN = "<image_special>"
        IMAGE_END_TOKEN = "</image_special>"
        NAVIGATION_SPECIAL_TOKEN = "[Navigation]"
        IAMGE_SEPARATOR = "<image_sep>"
        
        image_start_special_token = self.tokenizer(IMAGE_START_TOKEN, return_tensors="pt").input_ids[0][1:].cuda()
        image_end_special_token = self.tokenizer(IMAGE_END_TOKEN, return_tensors="pt").input_ids[0][1:].cuda()
        video_start_special_token = self.tokenizer(VIDEO_START_SPECIAL_TOKEN, return_tensors="pt").input_ids[0][1:].cuda()
        video_end_special_token = self.tokenizer(VIDEO_END_SPECIAL_TOKEN, return_tensors="pt").input_ids[0][1:].cuda()
        navigation_special_token = self.tokenizer(NAVIGATION_SPECIAL_TOKEN, return_tensors="pt").input_ids[0][1:].cuda()
        image_seperator = self.tokenizer(IAMGE_SEPARATOR, return_tensors="pt").input_ids[0][1:].cuda()

        if self.model.config.mm_use_im_start_end:
            qs = DEFAULT_IM_START_TOKEN + DEFAULT_IMAGE_TOKEN + DEFAULT_IM_END_TOKEN + '\n' + qs.replace('<image>', '')
        else:
            qs = DEFAULT_IMAGE_TOKEN + '\n' + qs.replace('<image>', '')

        conv = conv_templates[self.conv_mode].copy()
        conv.append_message(conv.roles[0], qs)
        conv.append_message(conv.roles[1], None)
        prompt = conv.get_prompt()
        
        token_prompt = tokenizer_image_token(prompt, self.tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').cuda()
        indices_to_replace = torch.where(token_prompt == -200)[0]
        new_list = []
        while indices_to_replace.numel() > 0:
            idx = indices_to_replace[0]
            new_list.append(token_prompt[:idx])
            new_list.append(video_start_special_token)
            new_list.append(image_seperator)
            new_list.append(token_prompt[idx:idx + 1])
            new_list.append(video_end_special_token)
            new_list.append(image_start_special_token)
            new_list.append(image_end_special_token)
            new_list.append(navigation_special_token)
            token_prompt = token_prompt[idx + 1:]
            indices_to_replace = torch.where(token_prompt == -200)[0]
        if token_prompt.numel() > 0:
            new_list.append(token_prompt)
        input_ids = torch.cat(new_list, dim=0).unsqueeze(0)

        stop_str = conv.sep if conv.sep_style != SeparatorStyle.TWO else conv.sep2
        keywords = [stop_str]
        stopping_criteria = KeywordsStoppingCriteria(keywords, self.tokenizer, input_ids)

        imgs = self.process_images(self.rgb_list)
        self.rgb_list = []

        cur_prompt = question
        with torch.inference_mode():
            self.model.update_prompt([[cur_prompt]])
            output_ids = self.model.generate(
                input_ids,
                images=imgs,
                do_sample=True,
                temperature=0.2,  # 与离线代码一致
                max_new_tokens=1024,
                use_cache=True,
                stopping_criteria=[stopping_criteria]
            )

        input_token_len = input_ids.shape[1]
        n_diff_input_output = (input_ids != output_ids[:, :input_token_len]).sum().item()
        if n_diff_input_output > 0:
            print(f'[Warning] {n_diff_input_output} output_ids are not the same as the input_ids')
        
        outputs = self.tokenizer.batch_decode(output_ids[:, input_token_len:], skip_special_tokens=True)[0]
        outputs = outputs.strip()
        if outputs.endswith(stop_str):
            outputs = outputs[:-len(stop_str)]
        outputs = outputs.strip()

        return outputs

    def reset(self, task_type='vln'):
        self.transformation_list = []
        self.rgb_list = []
        self.last_action = None
        self.count_id += 1
        self.count_stop = 0
        self.pending_action_list = []
        self.task_type = task_type
        self.first_forward = False
        self.executed_steps = 0
        self.model.config.run_type = "eval"
        self.model.get_model().initialize_online_inference_nav_feat_cache()
        self.model.get_model().new_frames = 0

    def act(self, data):
        
        img = data["image"]  # 假设客户端发送单张图片，字段名为 "image"
        self.rgb_list = [img]  # 放入列表，因为 process_images 需要列表
        print(f"[Inference] Image sequence length: {len(self.rgb_list)}")
    
        # 生成导航指令
        navigation_qs = self.promt_template.format(data["instruction"])
        navigation = self.predict_inference(navigation_qs)
        
        print(f"\n[Step {self.executed_steps + 1} Model Output]")
        print(f"Raw navigation string: '{navigation}'")
        print(f"Split actions: {navigation.split()}")
        
        action_list = navigation.split(" ")
        traj = [[0.0, 0.0, 0.0]]
        
        for action in action_list:
            if action == "stop":
                waypoint = [x + y for x, y in zip(traj[-1], [0.0, 0.0, 0.0])]
                traj = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
                break
            elif action == "forward":
                waypoint = [x + y for x, y in zip(traj[-1], [0.5, 0.0, 0.0])]
                traj.append(waypoint)
            elif action == "left":
                waypoint = [x + y for x, y in zip(traj[-1], [0.0, 0.0, -np.deg2rad(30)])]
                traj.append(waypoint)
            elif action == "right":
                waypoint = [x + y for x, y in zip(traj[-1], [0.0, 0.0, np.deg2rad(30)])]
                traj.append(waypoint)
        
        if len(action_list) == 0:
            raise ValueError("No action found in the output")
        
        self.executed_steps += 1
        self.latest_action = {"step": self.executed_steps, "path": [traj], "actions": action_list}
        return self.latest_action.copy()

# 全局变量，在启动时加载模型
agent = None

@app.on_event("startup")
async def startup_event():
    global agent
    print("Loading model...")
    model_path = "/root/autodl-tmp/Uni-NaVid/model_zoo/uninavid_weights/uninavid-7b-full-224-video-fps-1-grid-2"
    agent = UniNaVid_Agent(model_path)
    print("Model loaded successfully")

@app.post("/generate")
async def generate(data: dict):
    try:
        instruction = data.get("instruction", "")
        # 获取单张图片的 base64 字符串（字段名应为 "image"）
        image_b64 = data.get("image", "")
        reset_flag = data.get("reset", False)
        
        if not instruction:
            raise HTTPException(status_code=400, detail="No instruction provided")
        if not image_b64:
            raise HTTPException(status_code=400, detail="No image provided")

        if reset_flag:
            agent.reset()
            print("Agent history reset due to new instruction")
        # 解码单张图片
        img_bytes = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image")
        
        # 调用 agent.act，传入单张图片和指令
        result = agent.act({"instruction": instruction, "image": img})
        
        # 返回动作序列
        return {
            "response": {
                "actions": result["actions"],
                "traj": result["path"][0]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok", "model_loaded": agent is not None}

if __name__ == "__main__":
    # 使用 0.0.0.0 允许外部访问，端口 6008
    uvicorn.run(app, host="0.0.0.0", port=6008)