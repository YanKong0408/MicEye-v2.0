import json
import cv2

def visualize_coco_dataset(dataset_path, image_dir):
    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    images = dataset["images"]
    annotations = dataset["annotations"]
    categories = dataset["categories"]

    category_dict = {category["id"]: category["name"] for category in categories}

    for image_info in images:
        image_id = image_info["id"]
        image_path = image_info["file_name"]
        image = cv2.imread(image_path)
        height, width, _ = image.shape

        for ann in annotations:
            if ann["image_id"] == image_id:
                bbox = ann["bbox"]
                x, y, w, h = map(int, bbox)
                category_id = ann["category_id"]
                category_name = category_dict[category_id]

                cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(image, category_name, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("Image", image)
        cv2.waitKey(0)

    cv2.destroyAllWindows()

# 示例用法
dataset_path = "D:\\fungus_cjd\\annotations\\train.json"  # COCO数据集JSON文件路径
image_dir = "path/to/images"  # 图像文件夹路径
visualize_coco_dataset(dataset_path, image_dir)