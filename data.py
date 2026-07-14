import os
import cv2
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

def rgb_to_lab(rgb):
    # 人間の目の知覚に近い色空間に変換
    rgb_pixel = np.uint8([[rgb]])
    lab_pixel = cv2.cvtColor(rgb_pixel, cv2.COLOR_RGB2Lab)
    return lab_pixel[0][0].astype(float)

def get_lab_distance(c1, c2):
    # 人間の目基準での色差を計算
    lab1 = rgb_to_lab(c1)
    lab2 = rgb_to_lab(c2)
    return np.sqrt(np.sum((lab1 - lab2) ** 2))

def analyze_poster_flexible(path, max_colors=5):
    image = cv2.imread(path)
    if image is None: return None
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (150, 150))
    pixels = image.reshape(-1, 3)

    # 💡 まずは10色に細かく分けてグラデーションなどをすくい取る
    kmeans = KMeans(n_clusters=10, n_init=4, random_state=42)
    kmeans.fit(pixels)
    colors = kmeans.cluster_centers_.astype(int)
    ratios = np.bincount(kmeans.labels_) / len(pixels)

    # 💡 「似たような色」を人間基準の感覚（しきい値30）で綺麗にマージする
    threshold = 30 
    merged_colors = []
    merged_ratios = []
    sorted_indices = np.argsort(ratios)[::-1]
    
    for idx in sorted_indices:
        c, r = colors[idx], ratios[idx]
        found = False
        for i in range(len(merged_colors)):
            if get_lab_distance(c, merged_colors[i]) < threshold:
                merged_ratios[i] += r # 似た色なら割合を合算
                found = True
                break
        if not found:
            merged_colors.append(c)
            merged_ratios.append(r)

    # 割合の多い順に最大5色だけを厳選（1%未満のゴミはカット）
    final_colors = []
    final_ratios = []
    for c, r in zip(merged_colors, merged_ratios):
        if r >= 0.01:
            final_colors.append(c)
            final_ratios.append(r)
        if len(final_colors) >= max_colors:
            break
            
    return final_colors, final_ratios

def run_phase2(folder_path):
    results = []
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    files.sort()

    print("⏳ 知覚マージ版データベースを作成中...")
    for filename in files:
        path = os.path.join(folder_path, filename)
        try:
            analysis = analyze_poster_flexible(path)
            if analysis:
                colors, ratios = analysis
                row = {"filename": filename, "num_actual_colors": len(colors)}
                
                # 存在する色の分だけデータを詰める（足りない分は空っぽにする）
                for i in range(5):
                    if i < len(colors):
                        row[f"color{i+1}_r"] = colors[i][0]
                        row[f"color{i+1}_g"] = colors[i][1]
                        row[f"color{i+1}_b"] = colors[i][2]
                        row[f"ratio{i+1}"] = ratios[i]
                    else:
                        row[f"color{i+1}_r"] = row[f"color{i+1}_g"] = row[f"color{i+1}_b"] = row[f"ratio{i+1}"] = None
                results.append(row)
        except Exception as e:
            print(f"❌ {filename}: {e}")

    df = pd.DataFrame(results)
    df.to_csv("posters_dataset.csv", index=False)
    print(f"✨ 完了！データが綺麗にまとまりました。")

run_phase2("image")