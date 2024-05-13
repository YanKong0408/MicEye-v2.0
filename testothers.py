# import os
# import shutil

# # 原始图片文件夹路径
# folder_path = r"E:\Fungus\self_bbox_gaze\pic"
# # 分割后的文件夹路径
# output_folder = r"E:\Fungus\self_bbox_gaze\pic_split"

# # 创建分割后的文件夹
# os.makedirs(output_folder, exist_ok=True)

# # 获取文件夹中的所有图片文件
# image_files = [file for file in os.listdir(folder_path) if file.endswith((".jpg", ".jpeg", ".png"))]

# # 确保图片数量能够被 8 整除
# num_images = len(image_files)
# if num_images % 8 != 0:
#     print("图片数量无法被8整除")
#     exit()

# # 每份图片的数量
# images_per_split = num_images // 8

# # 分割图片并保存到不同的文件夹
# for i in range(8):
#     start_index = i * images_per_split
#     end_index = (i + 1) * images_per_split
#     split_images = image_files[start_index:end_index]

#     # 创建当前分割的文件夹
#     split_folder = os.path.join(output_folder, f"split_{i+1}")
#     os.makedirs(split_folder, exist_ok=True)

#     # 移动图片到当前分割的文件夹
#     for image_file in split_images:
#         src_path = os.path.join(folder_path, image_file)
#         dst_path = os.path.join(split_folder, image_file)
#         shutil.move(src_path, dst_path)

#     print(f"已将 {len(split_images)} 张图片移动到 {split_folder}")

# print("图片分割完成")
import math
print(3.34E22*(267.54E6)**2*(6.63E-34)**2*4.7/16/3.14/3.14/1.38E-34/300)