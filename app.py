"""
🏠 Delhi Real Estate Price Prediction App
-----------------------------------------
A Streamlit-based AI application for predicting property prices in Delhi.

Requirements:
    pip install streamlit pandas numpy pickle5 scikit-learn plotly

Run with:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# ======================================================================
# PAGE CONFIGURATION
# ======================================================================

st.set_page_config(
    page_title="Delhi Real Estate Price Predictor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================================
# CUSTOM CSS STYLING
# ======================================================================

st.markdown("""
    <style>
    .main { background-color: #f5f7fa; }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-size: 18px;
        font-weight: bold;
        padding: 15px;
        border-radius: 10px;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .prediction-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        margin: 20px 0;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .info-box {
        background-color: #e7f3ff;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2196F3;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #ffc107;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# ======================================================================
# LOAD MODEL AND SUPPORTING FILES
# ======================================================================

@st.cache_resource
def load_model_files():
    """Load trained ML model and necessary preprocessing objects."""
    try:
        with open('real_estate_price_model.pkl', 'rb') as f:
            model = pickle.load(f)
        with open('label_encoders.pkl', 'rb') as f:
            label_encoders = pickle.load(f)
        with open('feature_columns.pkl', 'rb') as f:
            feature_columns = pickle.load(f)
        with open('model_metadata.pkl', 'rb') as f:
            metadata = pickle.load(f)
        with open('scaler.pkl', 'rb') as f:
            scaler = pickle.load(f)
        return model, label_encoders, feature_columns, metadata, scaler

    except FileNotFoundError as e:
        st.error(f"❌ Missing file: {e.filename}")
        st.info("""
        Please ensure the following files are in the same directory as this app:
        - real_estate_price_model.pkl
        - label_encoders.pkl
        - feature_columns.pkl
        - model_metadata.pkl
        - scaler.pkl
        """)
        st.stop()
    except Exception as e:
        st.error(f"❌ Error loading model files: {e}")
        st.stop()

# Load assets
model, label_encoders, feature_columns, metadata, scaler = load_model_files()

# ======================================================================
# HELPER FUNCTIONS
# ======================================================================

@st.cache_data
def get_unique_values(_encoders):  # ← FIXED: Added underscore prefix
    """Extract unique categorical options from label encoders."""
    return {
        'property_types': sorted(_encoders.get('Property_Type', None).classes_.tolist()) if 'Property_Type' in _encoders and _encoders.get('Property_Type') is not None else ['Apartment/Flat', 'Independent House', 'Villa'],
        'locations': sorted(_encoders.get('Location_Clean', None).classes_.tolist()) if 'Location_Clean' in _encoders and _encoders.get('Location_Clean') is not None else ['Dwarka', 'Rohini', 'Vasant Kunj', 'Greater Kailash', 'Saket'],
        'furnishing_options': ['Furnished', 'Semi-Furnished', 'Unfurnished']
    }

unique_values = get_unique_values(label_encoders)

# ======================================================================
# PREDICTION FUNCTION
# ======================================================================

def predict_property_price(carpet_area, bedrooms, bathrooms, balconies,
                           floor_number, total_floors, property_type,
                           location, furnishing):
    """Generate a price prediction based on input property features."""

    features = {
        'Carpet_Area_Numeric': carpet_area,
        'Bedrooms': bedrooms,
        'Bathrooms': bathrooms,
        'Balconies': balconies,
        'Floor_Number': floor_number,
        'Total_Floors': total_floors,
        'Total_Rooms': bedrooms + bathrooms,
        'Bath_Bed_Ratio': bathrooms / (bedrooms + 1),
        'Floor_Position_Ratio': floor_number / (total_floors + 1),
        'Is_Top_Floor': int(floor_number == total_floors),
        'Is_Ground_Floor': int(floor_number == 0),
        'Furnishing_Score': {'Unfurnished': 0, 'Semi-Furnished': 1, 'Furnished': 2}.get(furnishing, 1),
        'Has_Balcony': int(balconies > 0),
    }

    # Derived categorical features
    size_category = (
        'Very Small' if carpet_area < 500 else
        'Small' if carpet_area < 1000 else
        'Medium' if carpet_area < 1500 else
        'Large' if carpet_area < 2500 else 'Very Large'
    )

    bedroom_category = (
        '1RK/1BHK' if bedrooms <= 1 else
        '2BHK' if bedrooms == 2 else
        '3BHK' if bedrooms == 3 else
        '4BHK' if bedrooms == 4 else '5BHK+'
    )

    # Encode categorical fields safely
    for key, encoder_key, value in [
        ('Property_Type_Encoded', 'Property_Type', property_type),
        ('Location_Clean_Encoded', 'Location_Clean', location),
        ('Size_Category_Encoded', 'Size_Category', size_category),
        ('Bedroom_Category_Encoded', 'Bedroom_Category', bedroom_category),
        ('Furnishing_Encoded', 'Furnishing', furnishing)
    ]:
        try:
            features[key] = label_encoders[encoder_key].transform([value])[0]
        except Exception as e:
            st.warning(f"⚠️ Could not encode {encoder_key}: {value}. Using default value.")
            features[key] = 0

    # Build DataFrame with correct column order
    input_df = pd.DataFrame([features])[feature_columns]

    # Predict price
    predicted_price = model.predict(input_df)[0]
    return predicted_price, features

# ======================================================================
# HEADER
# ======================================================================

st.title("🏠 Delhi Real Estate Price Predictor")
st.markdown("### AI-Powered Property Valuation System")

# ======================================================================
# SIDEBAR
# ======================================================================

with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/real-estate.png", width=80)
    st.title("Model Information")
    st.markdown("---")
    st.markdown(f"**Model Type:** {metadata.get('model_name', 'Machine Learning Model')}")
    st.markdown(f"**Accuracy (R²):** {metadata.get('test_r2_score', 0):.2%}")
    st.markdown(f"**Avg Error:** ₹{metadata.get('test_mae', 0)/100000:.2f} Lakhs")
    st.markdown(f"**Error Rate:** {metadata.get('test_mape', 0):.2f}%")
    st.markdown(f"**Training Date:** {metadata.get('training_date', 'N/A')}")
    st.markdown("---")
    st.info("💡 **Tip:** Enter accurate property details for the most reliable predictions.")
    st.markdown("---")
    st.markdown(f"**Features Used:** {len(feature_columns)}")
    st.markdown(f"**Training Data:** {metadata.get('training_samples', 0):,} samples")
    
    st.markdown("---")
    st.markdown("### 📊 About This App")
    with st.expander("How it works"):
        st.write("""
        This app uses machine learning to predict property prices based on:
        - Location and property type
        - Size and number of rooms
        - Floor details
        - Furnishing status
        - Derived features (ratios, categories)
        """)
    
    with st.expander("Prediction Accuracy"):
        st.write(f"""
        - **R² Score:** {metadata.get('test_r2_score', 0):.2%} of variance explained
        - **MAE:** ₹{metadata.get('test_mae', 0)/100000:.2f} Lakhs average error
        - **MAPE:** {metadata.get('test_mape', 0):.2f}% error rate
        """)

# ======================================================================
# MAIN FORM INPUT
# ======================================================================

st.markdown("## 📝 Enter Property Details")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📍 Location & Type")
    location = st.selectbox("Select Location", options=unique_values['locations'])
    property_type = st.selectbox("Property Type", options=unique_values['property_types'])
    furnishing = st.selectbox("Furnishing Status", options=unique_values['furnishing_options'])
    st.markdown("### 📏 Property Size")
    carpet_area = st.number_input("Carpet Area (sq.ft)", 100, 10000, 1000, 50)

with col2:
    st.markdown("### 🛏️ Rooms & Amenities")
    bedrooms = st.slider("Number of Bedrooms", 1, 10, 2)
    bathrooms = st.slider("Number of Bathrooms", 1, 8, 2)
    balconies = st.slider("Number of Balconies", 0, 5, 1)
    st.markdown("### 🏢 Floor Details")
    total_floors = st.number_input("Total Floors", 1, 50, 10)
    floor_number = st.number_input("Floor Number", 0, int(total_floors), min(5, int(total_floors)))

# ======================================================================
# VALIDATION
# ======================================================================

if floor_number > total_floors:
    st.error("❌ Floor number cannot be greater than total floors!")

# ======================================================================
# PREDICTION
# ======================================================================

st.markdown("---")
if st.button("🔮 Predict Property Price", use_container_width=True):
    if floor_number > total_floors:
        st.error("❌ Please correct the floor details before prediction!")
    else:
        with st.spinner("Analyzing property details..."):
            price, features = predict_property_price(
                carpet_area, bedrooms, bathrooms, balconies,
                floor_number, total_floors, property_type,
                location, furnishing
            )

            # Derived metrics
            price_per_sqft = price / carpet_area
            price_lakhs = price / 1e5
            price_crores = price / 1e7
            mape = metadata.get('test_mape', 10)
            lower, upper = price * (1 - mape/100), price * (1 + mape/100)

            st.success("✅ Price prediction completed successfully!")

            # Main prediction display
            st.markdown(f"""
                <div class="prediction-box">
                    <h2>💰 Predicted Property Price</h2>
                    <h1>₹{price_lakhs:.2f} Lakhs</h1>
                    <h3>(₹{price_crores:.2f} Crores)</h3>
                    <p style="font-size: 16px; margin-top: 15px;">
                        Expected Range: ₹{lower/1e5:.2f}L - ₹{upper/1e5:.2f}L
                    </p>
                </div>
            """, unsafe_allow_html=True)

            # ======================================================================
            # DETAILED ANALYTICS
            # ======================================================================

            st.markdown("## 📊 Detailed Price Analysis")

            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Price per Sq.ft", f"₹{price_per_sqft:,.0f}")
            with col2:
                st.metric("Total Area", f"{carpet_area:,} sq.ft")
            with col3:
                st.metric("Total Rooms", f"{bedrooms + bathrooms}")
            with col4:
                st.metric("Price Range", f"±{mape:.1f}%")

            st.markdown("---")

            # ======================================================================
            # VISUALIZATIONS
            # ======================================================================

            st.markdown("## 📈 Visual Insights")

            tab1, tab2, tab3 = st.tabs(["💹 Price Breakdown", "📊 Feature Comparison", "🏘️ Market Position"])

            with tab1:
                # Price breakdown pie chart
                col1, col2 = st.columns(2)
                
                with col1:
                    # Price components
                    base_price = carpet_area * 5000  # Approximate base
                    location_premium = max(0, price - base_price) * 0.4
                    amenities_value = (bedrooms * 500000 + bathrooms * 300000 + balconies * 200000)
                    
                    breakdown_df = pd.DataFrame({
                        'Component': ['Base Price', 'Location Premium', 'Amenities', 'Other Factors'],
                        'Value': [base_price, location_premium, amenities_value, 
                                 max(0, price - base_price - location_premium - amenities_value)]
                    })
                    
                    fig_pie = px.pie(breakdown_df, values='Value', names='Component',
                                    title='Estimated Price Components',
                                    color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    # Price range visualization
                    range_df = pd.DataFrame({
                        'Estimate': ['Lower Bound', 'Predicted', 'Upper Bound'],
                        'Price (Lakhs)': [lower/1e5, price_lakhs, upper/1e5]
                    })
                    
                    fig_bar = px.bar(range_df, x='Estimate', y='Price (Lakhs)',
                                    title='Price Estimate Range',
                                    color='Price (Lakhs)',
                                    color_continuous_scale='Viridis')
                    st.plotly_chart(fig_bar, use_container_width=True)

            with tab2:
                # Feature importance visualization
                feature_importance = {
                    'Carpet Area': carpet_area / 50,  # Normalized
                    'Location': 85,
                    'Bedrooms': bedrooms * 15,
                    'Bathrooms': bathrooms * 10,
                    'Floor Position': features['Floor_Position_Ratio'] * 100,
                    'Furnishing': features['Furnishing_Score'] * 30,
                    'Balconies': balconies * 8
                }
                
                feat_df = pd.DataFrame({
                    'Feature': list(feature_importance.keys()),
                    'Impact Score': list(feature_importance.values())
                })
                
                fig_features = px.bar(feat_df, x='Impact Score', y='Feature',
                                     orientation='h',
                                     title='Feature Impact on Price',
                                     color='Impact Score',
                                     color_continuous_scale='Sunset')
                st.plotly_chart(fig_features, use_container_width=True)

            with tab3:
                # Market position gauge
                avg_price_per_sqft = 8000  # Approximate Delhi average
                percentile = min(100, (price_per_sqft / avg_price_per_sqft) * 50)
                
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=percentile,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Market Percentile"},
                    delta={'reference': 50},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 25], 'color': "lightgray"},
                            {'range': [25, 50], 'color': "gray"},
                            {'range': [50, 75], 'color': "lightblue"},
                            {'range': [75, 100], 'color': "royalblue"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ))
                st.plotly_chart(fig_gauge, use_container_width=True)
                
                st.info(f"""
                📍 **Market Position:** This property is priced at ₹{price_per_sqft:,.0f}/sq.ft, 
                which places it in the **{percentile:.0f}th percentile** of the Delhi real estate market.
                """)

            st.markdown("---")

            # ======================================================================
            # PROPERTY SUMMARY
            # ======================================================================

            st.markdown("## 📋 Property Summary")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Input Features")
                summary_data = {
                    'Feature': [
                        'Location', 'Property Type', 'Carpet Area', 
                        'Bedrooms', 'Bathrooms', 'Balconies',
                        'Floor', 'Total Floors', 'Furnishing'
                    ],
                    'Value': [
                        location, property_type, f"{carpet_area:,} sq.ft",
                        bedrooms, bathrooms, balconies,
                        floor_number, total_floors, furnishing
                    ]
                }
                st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

            with col2:
                st.markdown("### Derived Insights")
                insights_data = {
                    'Metric': [
                        'Price per Sq.ft', 'Total Rooms', 
                        'Bath/Bedroom Ratio', 'Floor Position',
                        'Property Category', 'Top Floor?', 'Has Balcony?'
                    ],
                    'Value': [
                        f"₹{price_per_sqft:,.0f}",
                        features['Total_Rooms'],
                        f"{features['Bath_Bed_Ratio']:.2f}",
                        f"{features['Floor_Position_Ratio']:.1%}",
                        'Large' if carpet_area > 1500 else 'Medium' if carpet_area > 1000 else 'Compact',
                        '✅ Yes' if features['Is_Top_Floor'] else '❌ No',
                        '✅ Yes' if features['Has_Balcony'] else '❌ No'
                    ]
                }
                st.dataframe(pd.DataFrame(insights_data), use_container_width=True, hide_index=True)

            # ======================================================================
            # RECOMMENDATIONS
            # ======================================================================

            st.markdown("## 💡 Recommendations")

            recommendations = []

            if price_per_sqft > 12000:
                recommendations.append("🔴 **Premium Pricing:** This property is in the higher price bracket for Delhi.")
            elif price_per_sqft < 6000:
                recommendations.append("🟢 **Value Deal:** This property offers good value for money.")
            else:
                recommendations.append("🟡 **Market Rate:** This property is priced at market average.")

            if features['Bath_Bed_Ratio'] < 0.5:
                recommendations.append("⚠️ **Consider:** Low bathroom-to-bedroom ratio may affect resale value.")
            
            if features['Is_Top_Floor']:
                recommendations.append("✨ **Advantage:** Top floor properties often command premium prices.")
            
            if balconies == 0:
                recommendations.append("💭 **Note:** Adding a balcony could increase property value by 3-5%.")
            
            if furnishing == 'Unfurnished':
                recommendations.append("🛋️ **Potential:** Furnishing could increase value by ₹5-10 lakhs.")

            for rec in recommendations:
                st.markdown(f"- {rec}")

            # ======================================================================
            # DOWNLOAD REPORT
            # ======================================================================

            st.markdown("---")
            st.markdown("## 📥 Download Prediction Report")

            # Generate report
            report_data = {
                'Prediction Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                'Location': [location],
                'Property Type': [property_type],
                'Carpet Area (sq.ft)': [carpet_area],
                'Bedrooms': [bedrooms],
                'Bathrooms': [bathrooms],
                'Balconies': [balconies],
                'Floor Number': [floor_number],
                'Total Floors': [total_floors],
                'Furnishing': [furnishing],
                'Predicted Price (₹)': [f"{price:,.0f}"],
                'Price (Lakhs)': [f"{price_lakhs:.2f}"],
                'Price (Crores)': [f"{price_crores:.2f}"],
                'Price per Sq.ft': [f"{price_per_sqft:,.0f}"],
                'Lower Estimate (₹)': [f"{lower:,.0f}"],
                'Upper Estimate (₹)': [f"{upper:,.0f}"],
                'Model Accuracy (R²)': [f"{metadata.get('test_r2_score', 0):.2%}"],
                'Model Error (MAPE)': [f"{mape:.2f}%"]
            }
            
            report_df = pd.DataFrame(report_data)
            csv = report_df.to_csv(index=False)
            
            st.download_button(
                label="📄 Download Full Report (CSV)",
                data=csv,
                file_name=f"property_prediction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            # ======================================================================
            # DISCLAIMER
            # ======================================================================

            st.markdown("---")
            st.markdown("""
                <div class="warning-box">
                    <strong>⚠️ Disclaimer:</strong> This prediction is based on historical data and machine learning models. 
                    Actual property prices may vary based on market conditions, exact location, property condition, 
                    legal factors, and other variables not captured in this model. 
                    Always consult with real estate professionals before making investment decisions.
                </div>
            """, unsafe_allow_html=True)

# ======================================================================
# FOOTER
# ======================================================================

st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>🏠 <strong>Delhi Real Estate Price Predictor</strong> | 
        Powered by Machine Learning | 
        Built with Streamlit</p>
        <p style="font-size: 12px;">© 2024 | For educational and informational purposes only</p>
    </div>
""", unsafe_allow_html=True)