# 🏠 Delhi Real Estate Price Prediction System

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.50.0-red.svg)
![Scikit-learn](https://img.shields.io/badge/Scikit--learn-1.7.2-orange.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-3.1.0-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**An AI-powered web application for predicting real estate property prices in Delhi, India.**

[Features](#-features) • [Demo](#-demo) • [Installation](#-installation) • [Usage](#-usage) • [Model Training](#-model-training) • [API Documentation](#-api-documentation)

---

## 📋 Table of Contents   
-[Know more about web Scraper](scraper/scraper_technical_doc.md)

- [Overview](#-overview)
- [Features](#-features)
- [Demo](#-demo)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Usage](#-usage)
- [Model Training](#-model-training)
- [Project Structure](#-project-structure)
- [Dataset](#-dataset)
- [Model Performance](#-model-performance)
- [API Documentation](#-api-documentation)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)
- [Contact](#-contact)

---

## 🎯 Overview

The **Delhi Real Estate Price Prediction System** is a complete machine learning solution that predicts property rental and sale prices in Delhi based on features like location, size, amenities, and property type.

### Includes:
- 📊 **Data Cleaning & Feature Engineering Pipeline**
- 🤖 **Multiple ML Models** (Random Forest, XGBoost, LightGBM, Gradient Boosting)
- 🌐 **Interactive Web App** built with Streamlit
- 📈 **Advanced Visualizations** using Plotly
- 🔧 **Kaggle Notebook** for training and comparison

### Why This Project?
✅ Solves real-world property valuation problems  
✅ End-to-end ML pipeline from data to deployment  
✅ Production-ready code with validation and documentation  
✅ Scalable and educational design  

---

## ✨ Features

### 🔍 Data Processing
- Automated cleaning and preprocessing  
- Smart handling of missing values  
- Parsing prices (Lakhs, Crores, etc.)  
- Extracting floor info and removing outliers  

### 🧠 Machine Learning
- Multiple model comparison  
- 17+ engineered features  
- Hyperparameter tuning with GridSearchCV  
- Feature importance and validation  

### 🎨 Web Application
- Interactive Streamlit UI  
- Real-time predictions and visual analytics  
- Responsive design (desktop + mobile)  
- Downloadable prediction reports  

### 📊 Visualizations
- Price distributions  
- Correlation heatmaps  
- Interactive Plotly charts  
- Feature impact and importance visuals  

---

## 🎬 Demo

### Example Interface

### Sample Predictions

| Property | Predicted Price |
|-----------|----------------|
| 2BHK, 1000 sq.ft, Rohini | ₹35–40 Lakhs |
| 3BHK, 1800 sq.ft, Vasant Kunj | ₹70–80 Lakhs |
| 4BHK, 2500 sq.ft, Greater Kailash | ₹1.5–1.8 Crores |

---

## 🏗️ Architecture


---

## 🚀 Installation

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### 1️⃣ Clone Repository
```bash
git clone https://github.com/22bsm056/estate.git
cd estate
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
estate/
│
├── app.py
├── README.md
├── requirements.txt
├── data/
├── models/
│   ├── real_estate_price_model.pkl
│   ├── label_encoders.pkl
│   ├── feature_columns.pkl
│   ├── model_metadata.pkl
│   └── scaler.pkl
└── scraper/
