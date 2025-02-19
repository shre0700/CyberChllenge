import os
import pandas as pd
import nltk
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from nltk.sentiment import SentimentIntensityAnalyzer
import matplotlib
matplotlib.use("Agg")  # Fix for RuntimeError (Non-GUI backend)
import matplotlib.pyplot as plt
import seaborn as sns
import json  # Make sure to import json

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Download NLTK lexicon
nltk.download("vader_lexicon")

# Initialize Sentiment Analyzer
sia = SentimentIntensityAnalyzer()

UPLOAD_FOLDER = "uploads"
GRAPH_FOLDER = "graphs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GRAPH_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["GRAPH_FOLDER"] = GRAPH_FOLDER

# Define gang-related keywords
gang_keywords = {"turf", "shoot", "weapon", "hit", "deal", "crew", "rival", "pack", "smash", "stash",
                 "bullet", "knife", "trigger", "war", "retaliate", "threat", "trap", "blood", "cartel", "recruit"}

def classify_risk(message, score):
    words = set(str(message).lower().split())  
    keyword_count = len(words.intersection(gang_keywords))  

    if score <= -0.5 or keyword_count >= 2:
        return "High Risk"
    elif -0.5 < score <= -0.2 or keyword_count == 1:
        return "Medium Risk"
    else:
        return "Low Risk"

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"message": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    # Get keywords from request
    keywords = request.form.get("keywords")
    if keywords:
        keywords = json.loads(keywords)  # Convert JSON string to Python dict
    else:
        keywords = {"high": [], "medium": [], "low": []}

    print("Received Keywords:", keywords)  # Debugging

    try:
        # Read uploaded CSV file
        df = pd.read_csv(file_path)

        # Perform sentiment analysis
        df["Sentiment Score"] = df["Message"].apply(lambda text: sia.polarity_scores(str(text))["compound"])
        df["Sentiment Label"] = df["Sentiment Score"].apply(lambda score: "Positive" if score > 0.05 else ("Negative" if score < -0.05 else "Neutral"))

        # Modify gang-related keywords dynamically
        gang_keywords.update(set(keywords["high"] + keywords["medium"] + keywords["low"]))

        # Apply risk classification
        df["Risk Level"] = df.apply(lambda row: classify_risk(row["Message"], row["Sentiment Score"]), axis=1)

        # Save categorized data
        df.to_csv(os.path.join(app.config["UPLOAD_FOLDER"], "processed_chat_data.csv"), index=False)

        # Generate graphs
        generate_graphs(df)

        return jsonify({"message": "File processed successfully", "file_path": file_path})
    
    except Exception as e:
        return jsonify({"message": "Error processing file", "error": str(e)}), 500

def generate_graphs(df):
    """Generate graphs and save them as images."""
    
    # Sentiment Distribution Graph
    plt.figure(figsize=(8, 5))
    sns.countplot(x="Sentiment Label", data=df, palette="coolwarm", order=["Positive", "Neutral", "Negative"])
    plt.title("Sentiment Distribution of Chat Messages")
    plt.xlabel("Sentiment")
    plt.ylabel("Count")
    sentiment_graph_path = os.path.join(app.config["GRAPH_FOLDER"], "sentiment_distribution.png")
    plt.savefig(sentiment_graph_path)
    plt.close()

    # Risk Level Distribution Graph
    plt.figure(figsize=(8, 5))
    sns.countplot(x="Risk Level", data=df, palette="Reds", order=["Low Risk", "Medium Risk", "High Risk"])
    plt.title("Gang-Related Risk Level Distribution")
    plt.xlabel("Risk Level")
    plt.ylabel("Count")
    risk_graph_path = os.path.join(app.config["GRAPH_FOLDER"], "risk_distribution.png")
    plt.savefig(risk_graph_path)
    plt.close()

@app.route("/graph/<graph_type>", methods=["GET"])
def get_graph(graph_type):
    """Serve the requested graph."""
    graph_path = os.path.join(app.config["GRAPH_FOLDER"], f"{graph_type}.png")
    if os.path.exists(graph_path):
        return send_file(graph_path, mimetype="image/png")
    return jsonify({"message": "Graph not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
