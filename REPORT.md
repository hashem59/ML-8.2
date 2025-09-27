# SIT720 Week 8.2 — Melbourne Housing Price Prediction

This report documents the full workflow across the five required steps: data acquisition, preprocessing and EDA, model development, feature importance, and deployment.

### Step 1. Melbourne Housing Data Acquisition
- **Goal**: Collect at least 150 housing records per chosen suburb (≥50 minimum for each suburb used), including features like property type, bedrooms, bathrooms, parking, land size, sold date, and the target `sold_price`.
- **Suburbs**: Highton (VIC 3216), Ballarat (Greater Region, VIC), Werribee (VIC 3030).
- **Tooling**:
  - `housing_data_scraper.py` built with Selenium + BeautifulSoup.
  - Optional cookie loading from `www.realestate.com.au.cookies.json` to improve session stability.
  - Configured to iterate listing pages per suburb (up to 4 pages by default) targeting up to 150 records per suburb.
- **Output**: Data saved to `melbourne_housing_data.csv` with columns:
  - `suburb, address, property_type, bedrooms, bathrooms, parking, land_size, sold_price, sold_date, listing_url`.
- **Dataset used in modeling**: 300 rows across the three suburbs (unique suburbs confirmed: Highton, Ballarat, Werribee). This satisfies the “≥50 per suburb” requirement in the final dataset used for analysis.

### Step 2. Data Preprocessing and Exploratory Data Analysis (EDA)
- **Parsing and ordering**:
  - Converted `sold_date` to datetime and sorted by date (newest first).
- **Categorical encoding**:
  - One-hot encoding applied to `suburb` and `property_type` (no NaN dummy columns), producing columns like `suburb_Highton`, `property_type_House`, etc.
- **Feature engineering (leak-free)**:
  - Added: `land_per_bedroom = land_size / max(bedrooms, 1)`, `rooms_total = bedrooms + bathrooms`, temporal `sold_year`, `sold_month`.
  - Note: an intermediate feature `price_per_bedroom` was created only for EDA exploration and then explicitly REMOVED before modeling to avoid data leakage.
- **Numerical scaling**:
  - Standardization for numerical inputs: `bedrooms, bathrooms, parking, land_size` (and additional numeric features where present), using `StandardScaler`.
- **Missing values**:
  - Imputed `parking` with 0; imputed `land_size` via median during model preparation; sanitized engineered features (replace inf with NaN, then fill median).
- **Visualizations**:
  - Price distribution: histogram + KDE and box plot for `sold_price`.
  - Correlation heatmap for numerical features.
  - Outlier inspection via box plots of numerical columns.
  - Temporal trend: average `sold_price` over time by `suburb` line plot.

### Step 3. Model Development, Metrics, and Cross-Validation
- **Train/test split**: 80/20 random split with `random_state=42`.
- **Models** (scikit-learn):
  - Linear Regression
  - Random Forest Regressor (n_estimators=100, random_state=42)
  - Gradient Boosting Regressor (n_estimators=100, random_state=42)
- **Evaluation metrics**: MAE, RMSE, R².
- **Observed test-set results (representative run)**:
  - Linear Regression: MAE ≈ 91,878 | RMSE ≈ 127,814 | R² ≈ 0.711
  - Random Forest: MAE ≈ 110,759 | RMSE ≈ 176,737 | R² ≈ 0.447
  - Gradient Boosting: MAE ≈ 106,599 | RMSE ≈ 161,855 | R² ≈ 0.536
- **5-fold cross-validation** (mean ± 2×std, representative):
  - Linear Regression: MAE ≈ 112,972 | RMSE ≈ 167,835 | R² ≈ 0.547
  - Random Forest: MAE ≈ 108,937 | RMSE ≈ 175,416 | R² ≈ 0.518
  - Gradient Boosting: MAE ≈ 110,125 | RMSE ≈ 171,553 | R² ≈ 0.542
- **Takeaway**: Linear Regression generalized best on the test set for this dataset snapshot, while tree models showed stronger train fit but less generalization (suggesting mild overfitting without tuning).

### Step 4. Feature Importance
- **Linear Regression (absolute coefficients)**: Top signals among encoded features included `bathrooms`, `bedrooms`, and suburb/property-type indicators (e.g., `suburb_Highton`, `property_type_*`).
- **Random Forest / Gradient Boosting (feature_importances_)**: `land_size` ranked highest, followed by `bathrooms`, `bedrooms`, and `suburb` effects.
- **Interpretation**: Land size strongly influences price; bedroom/bathroom counts are robust predictors; location (suburb) and property type matter meaningfully.

### Step 5. Model Deployment (Web Demo)
- **Framework**: Gradio interface embedded in the notebook (`task.ipynb`).
- **Model served**: Linear Regression (best test-set R² in our run).
- **Inputs**: `suburb`, `property_type`, `bedrooms`, `bathrooms`, `parking`, `land_size` (with fallback to median when land size is unknown).
- **Output**: Predicted price as currency-formatted string.
- **How to run**:
  1. Ensure dependencies are installed (see below).
  2. In `task.ipynb`, scroll to the deployment cell and uncomment the `iface.launch(share=True)` line.
  3. Run the cell to launch the local and shareable demo URLs.

### Reproducibility and Environment
- **Key dependencies**: pandas, numpy, scikit-learn, matplotlib, seaborn, gradio.
- **Install** (from within Jupyter):
```python
%pip install -q pandas numpy scikit-learn matplotlib seaborn gradio
```
- **Data path**: Notebook expects `melbourne_housing_data.csv` in the project root. Update the path if you move the file.

### Notes and Good Practices
- Avoid target leakage: do not include target-derived features (e.g., `price_per_bedroom`) in training or inference.
- Consider hyperparameter tuning (Random Forest / Gradient Boosting) for further gains.
- Extend feature set (e.g., proximity to schools/transport) for richer signal.
- Re-run end-to-end after changes to validate metrics and plots.

---
If you need a brief, presentation-friendly summary, see the final section in `task.ipynb` under “Summary and Conclusions.”
