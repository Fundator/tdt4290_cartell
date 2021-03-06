import os
import argparse
import fleep

from api_setup import api_setup
from flask import request, jsonify
from model_utils import predict, load_model, load_image, get_labels

ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg"])


def allowed_file(file):
    info = fleep.get(file.read(128))
    if len(info.extension) != 0:
        return info.extension[0] in ALLOWED_EXTENSIONS  # magic number check
    else:  # Backup solution in case the magic number got stripped
        name, ext = os.path.splitext(file.filename)
        return ext and ext[1:] in ALLOWED_EXTENSIONS


@api_setup.route("/api", methods=["POST"])
def upload_file():
    # check if the post request has the file part
    if "file" not in request.files:
        resp = jsonify({"message": "No file part in the request"})
        resp.status_code = 400
        return resp
    file = request.files["file"]
    if file.filename == "":
        resp = jsonify({"message": "No file selected for uploading"})
        resp.status_code = 400
        return resp
    if file and allowed_file(file):
        file.seek(0) # in case file was read through earlier
        encoded_image = file.read()
        image = load_image(encoded_image, target_shape)

        # Here the image is fetched from the api, and correctly encoded for the model
        pred = predict(model, image, labels)  # Predict on the model
        pred = {x: float(pred[x]) for x in pred}  # Translate np float -> python float to allow it to be made to json
        resp = jsonify(pred)  # Build response as json
        resp.status_code = 200
        return resp
    else:
        resp = jsonify(
            {"message": "Allowed file types are png, jpg, jpeg"})
        resp.status_code = 400
        return resp


# A liveness test to check the status of the container
@api_setup.route("/liveness", methods=["GET"])
def liveness():
    return "OK"


def make_argparser():
    parser = argparse.ArgumentParser(description="Predict a desired car feature")
    parser.add_argument("-w", "--weights_path", default="./vehicle_brand_classification/efficientnetb0_512.hdf5",
            type=str, help="Path to weights for model")
    parser.add_argument("-l", "--label_path", default="./vehicle_brand_classification/brands.txt",
            type=str, help="Path to labels for model")
    parser.add_argument("--dev", default=False,
            type=bool, help="Run the server in dev-mode. NOT RECOMMENDED FOR PRODUCTION")
    return parser


if __name__ == "__main__":
    args = make_argparser().parse_args()

    # Initialize the model
    print("Loading labels and model")
    labels = get_labels(args.label_path)
    model = load_model(args.weights_path)
    target_shape = model.layers[0].input_shape[1:-1]
    print("Model was loaded succesfully.")

    if args.dev:
        # This runs the server in a less secure way
        # Enable https by adding ssl_context='adhoc' to run
        api_setup.run(host="0.0.0.0")
    else:
        # Run the server with the flask standard
        from waitress import serve
        serve(api_setup, host="0.0.0.0", port=5000)
