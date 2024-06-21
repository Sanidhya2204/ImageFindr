import os
from flask import Flask, render_template, request
from google.cloud import vision
import pandas as pd
import validators

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'tough-melody-426205-n0-85b29f2d2808.json'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads' 

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

csv_file = 'products.csv'
df = pd.read_csv(csv_file)

def localize_objects_uri(image_path):
    client = vision.ImageAnnotatorClient()

    if validators.url(image_path):
        image = vision.Image()
        image.source.image_uri = image_path
    else:
        try:
            with open(image_path, "rb") as image_file:
                content = image_file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File '{image_path}' not found.")
        except PermissionError:
            raise PermissionError(f"Permission denied accessing '{image_path}'.")

        image = vision.Image(content=content)

    objects = client.object_localization(image=image).localized_object_annotations

    detected_objects = []
    for obj in objects:
        detected_objects.append(obj.name.lower())

    return detected_objects

def check_if_exists(detected_objects):
    matching_products = []
    URLs = []
    for index, row in df.iterrows():
        if detected_objects == row['product_name'].lower():
            matching_products.append(row['product_name'])
            URLs.append(row['path'])
    return matching_products, URLs

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect_products', methods=['POST'])
def detect_products():
    if 'image_file' in request.files:
        image_file = request.files['image_file']
        if image_file.filename == '':
            return "No selected file"
        if 'image_file' not in request.files:
            return 'No file part in the request'
        image_file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
        image_file.save(image_file_path)
        detected_objects = localize_objects_uri(image_file_path)
    elif 'image_url' in request.form:
        try:
            image_url = request.form['image_url']
            detected_objects = localize_objects_uri(image_url)
        except Exception as e:
            return f'Error: {e}'

    else:
        return "No image file found."

    if detected_objects:
        matching_products = []
        URLs = []
        for obj in detected_objects:
            products, urls = check_if_exists(obj)
            matching_products.extend(products)
            URLs.extend(urls)

        if matching_products:
            return render_template('results.html', products=matching_products, urls=URLs, length=len(matching_products))
        else:
            no_results = "No matching products found."
            return render_template('results.html', no_results=no_results)
    else:
        return "No objects detected in the image."


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)

