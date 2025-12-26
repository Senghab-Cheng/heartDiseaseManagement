import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, confusion_matrix, 
    classification_report
)
import joblib
import os
from datetime import datetime
import warnings 
warnings.filterwarnings('ignore')

def load_data(filepath='heartDiseaseCleaned.csv'):
    """Load the heart disease dataset"""
    print("=" * 60)
    print("STEP 1: LOADING DATASET")
    print("=" * 60)
    
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found!")
        print("Please ensure 'heartDiseaseCleaned.csv' is in the project root")
        return None
    
    df = pd.read_csv(filepath)
    print(f"Dataset loaded successfully!")
    print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nTarget Distribution:")
    print(df.iloc[:, -1].value_counts())
    print()
    
    return df

def prepare_data(df):
    """Prepare data for training"""
    print("=" * 60)
    print("STEP 2: PREPARING DATA")
    print("=" * 60)
    
    X = df.iloc[:, :-1]
    # Last column (target)
    y = df.iloc[:, -1]

    print(f"Features: {X.shape[1]} columns")
    print(f"Target: {y.name if hasattr(y, 'name') else 'target'}")

    # Check for missing values
    missing = X.isnull().sum().sum()
    if missing > 0:
        print(f"Warning: {missing} missing values found. Filling with median...")
        X = X.fillna(X.median())
    else:
        print("No missing values")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f'\nTrain set: {X_train.shape[0]} samples')
    print(f'Test set: {X_test.shape[0]} samples')

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print('Features scaled using StandardScaler')
    print()

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler, X.columns.tolist()

def train_models(X_train, y_train):
    """Train multiple models and compare"""
    print("=" * 60)
    print("STEP 3: TRAINING MODELS")
    print("=" * 60)
    
    models = {
        'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'KNN': KNeighborsClassifier(n_neighbors=7)
    }
    
    trained_models = {}
    cv_scores = {}

    for name, model in models.items():
        print(f'\nTraining {name}...')

        try:
            model.fit(X_train, y_train)
            
            cv_score = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')
            cv_scores[name] = cv_score

            trained_models[name] = model

            print(f'   {name} trained')
            print(f'   CV AUC Score: {cv_score.mean():.4f} (+/- {cv_score.std():.4f})')
        except Exception as e:
            print(f'   {name} failed: {str(e)}')
            continue

    best_model_name = max(cv_scores, key=lambda k: cv_scores[k].mean())
    best_model = trained_models[best_model_name]

    print(f'\n{"="*60}')
    print('MODEL COMPARISON (Top 3)')
    print(f'{"="*60}')

    sorted_models = sorted(cv_scores.items(), key=lambda x: x[1].mean(), reverse=True)

    print('\nModels Ranked by Performance:')
    for i, (name, scores) in enumerate(sorted_models, 1):
        print(f"   {i}. {name:20s} : {scores.mean():.4f} (+/- {scores.std():.4f})")

    print(f"\nWinner: {best_model_name}")
    print(f'   AUC Score: {cv_scores[best_model_name].mean():.4f}')
    print()
    
    return best_model, best_model_name, trained_models, cv_scores

def evaluate_model(model, X_test, y_test, model_name):
    """Evaluate model performance"""
    print('=' * 60) 
    print(f'STEP 4: EVALUATING {model_name}')
    print('=' * 60)

    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)

    print(f"\nModel Performance:")
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1 Score:  {f1:.4f}")
    print(f"   ROC AUC:   {roc_auc:.4f}")

    cm = confusion_matrix(y_test, y_pred)
    print(f"\nConfusion Matrix:")
    print(f"   True Negatives:  {cm[0][0]}")
    print(f"   False Positives: {cm[0][1]}")
    print(f"   False Negatives: {cm[1][0]}")
    print(f"   True Positives:  {cm[1][1]}")

    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['No Disease', 'Disease']))
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'roc_auc': roc_auc,
        'confusion_matrix': cm
    }

def save_model(model, scaler, feature_names, model_name, metrics):
    """Save trained model and artifacts"""
    print('=' * 60)
    print('STEP 5: SAVING MODEL')
    print('=' * 60)

    os.makedirs('models', exist_ok=True)
    
    model_path = 'models/heart_disease_model.pkl'
    joblib.dump(model, model_path)
    print(f"Model saved: {model_path}")
    
    scaler_path = 'models/scaler.pkl'
    joblib.dump(scaler, scaler_path)
    print(f"Scaler saved: {scaler_path}")
    
    features_path = 'models/feature_names.pkl'
    joblib.dump(feature_names, features_path)
    print(f"Feature names saved: {features_path}")

    metadata = {
        'model_name': model_name,
        'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'metrics': metrics,
        'feature_names': feature_names,
        'n_features': len(feature_names)
    }

    metadata_path = 'models/model_metadata.pkl'
    joblib.dump(metadata, metadata_path)
    print(f"Metadata saved: {metadata_path}")
    
    print(f"\nAll model artifacts saved in 'models/' directory")
    print()

def display_feature_importance(model, feature_names):
    """Display feature importance if available"""
    print("=" * 60)
    print("FEATURE IMPORTANCE")
    print("=" * 60)
    
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        print("\nTop 10 Most Important Features:")
        for i, idx in enumerate(indices[:10], 1):
            print(f"   {i:2d}. {feature_names[idx]:20s} : {importances[idx]:.4f}")
    else:
        print("This model doesn't provide feature importance")
    
    print()

def main():
    """Main training pipeline"""
    print("\n")
    print("=" * 60)
    print("   HEART DISEASE PREDICTION MODEL TRAINING")
    print("=" * 60)
    print()
    
    df = load_data()
    if df is None:
        return
    
    X_train, X_test, y_train, y_test, scaler, feature_names = prepare_data(df)
    best_model, best_model_name, all_models, cv_scores = train_models(X_train, y_train)
    metrics = evaluate_model(best_model, X_test, y_test, best_model_name)
    display_feature_importance(best_model, feature_names)
    save_model(best_model, scaler, feature_names, best_model_name, metrics)

    print("=" * 60)
    print("TRAINING COMPLETE!")
    print("=" * 60)
    print(f"\nModel Performance Summary:")
    print(f"   Model Type: {best_model_name}")
    print(f"   Accuracy:   {metrics['accuracy']*100:.2f}%")
    print(f"   ROC AUC:    {metrics['roc_auc']:.4f}")
    print(f"   Precision:  {metrics['precision']:.4f}")
    print(f"   Recall:     {metrics['recall']:.4f}")
    
    print(f"\nModel files saved in 'models/' directory:")
    print(f"   - heart_disease_model.pkl")
    print(f"   - scaler.pkl")
    print(f"   - feature_names.pkl")
    print(f"   - model_metadata.pkl")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        print(f"Please check your dataset and try again")
        import traceback
        traceback.print_exc()