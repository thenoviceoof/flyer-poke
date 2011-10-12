#!/usr/bin/env python

from flask import Flask, render_template, request
import sqlalchemy
import smtplib
import random
import os

app = Flask(__name__)

@app.route("/")
def landing():
    return render_template("index.html")

# @app.route("/login", methods=["POST"])
# def login():
#     return render_template("login.html")

@app.route("/list", methods=["GET", "POST"])
def list():
    return render_template("list.html")

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method=="POST":
        f = request.files['flyer']
        path = os.path.dirname(os.path.abspath(__file__))
        f.save(path+"/flyer/%05d-%s" % (random.randint(0,99999), f.filename))
    return render_template("upload.html")


if __name__ == "__main__":
    app.run(debug=True)
