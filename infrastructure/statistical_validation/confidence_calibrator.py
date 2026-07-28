"""
Confidence calibration system to ensure confidence scores reflect actual accuracy.
Uses Platt scaling or isotonic regression to calibrate confidence scores.
"""
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from typing import List, Tuple
import pickle
from datetime import datetime, timedelta
import os

class ConfidenceCalibrator:
    """Calibrates confidence scores to reflect actual prediction accuracy."""
    
    def __init__(self, model_type='isotonic', calibration_window=500, filepath=None):
        self.model_type = model_type
        self.calibration_window = calibration_window
        self.calibration_model = None
        self.calibration_data = []  # [(raw_confidence, actual_outcome), ...]
        self.last_calibration_time = None
        self.calibration_frequency = timedelta(hours=24)  # Recalibrate daily
        self.filepath = filepath
        
        # Auto-load on startup if filepath is set
        if self.filepath:
            self.load_model(self.filepath)
        
    def add_calibration_sample(self, raw_confidence: float, actual_outcome: bool):
        """Add a calibration sample (confidence, actual result)."""
        self.calibration_data.append((float(raw_confidence), bool(actual_outcome)))
        
        # Keep only the most recent samples
        if len(self.calibration_data) > self.calibration_window:
            self.calibration_data = self.calibration_data[-self.calibration_window:]
            
        # Recalibrate if enough new data points
        if len(self.calibration_data) >= 50 and self._should_recalibrate():
            self._recalibrate()
        elif self.filepath:
            # Even if we don't recalibrate, save the updated calibration data
            self.save_model(self.filepath)
            
    def calibrate_confidence(self, raw_confidence: float) -> float:
        """Calibrate a raw confidence score."""
        if self.calibration_model is None:
            # If no calibration model exists, return raw confidence
            return min(max(raw_confidence, 0.0), 1.0)
            
        try:
            calibrated = self.calibration_model.predict([raw_confidence])[0]
            return min(max(calibrated, 0.0), 1.0)
        except Exception:
            return min(max(raw_confidence, 0.0), 1.0)
        
    def _should_recalibrate(self) -> bool:
        """Check if recalibration is needed."""
        if self.last_calibration_time is None:
            return True
            
        return datetime.now() - self.last_calibration_time > self.calibration_frequency
        
    def _recalibrate(self):
        """Recalibrate the model with current data."""
        if len(self.calibration_data) < 10:  # Need minimum samples
            return
            
        confidences, outcomes = zip(*self.calibration_data)
        
        if self.model_type == 'isotonic':
            self.calibration_model = IsotonicRegression(out_of_bounds='clip')
        else:  # platt scaling
            self.calibration_model = LogisticRegression()
            
        # Fit the model
        X = np.array(confidences).reshape(-1, 1)
        y = np.array(outcomes)
        
        self.calibration_model.fit(X, y)
        self.last_calibration_time = datetime.now()
        
        # Auto-save after recalibration
        if self.filepath:
            self.save_model(self.filepath)
        
    def save_model(self, filepath: str):
        """Save the calibration model to disk."""
        try:
            dir_name = os.path.dirname(filepath)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            model_data = {
                'model': self.calibration_model,
                'model_type': self.model_type,
                'calibration_data': self.calibration_data,
                'last_calibration_time': self.last_calibration_time
            }
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
        except Exception:
            pass
            
    def load_model(self, filepath: str):
        """Load the calibration model from disk."""
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            return
            
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
                
            self.calibration_model = model_data.get('model')
            self.model_type = model_data.get('model_type', self.model_type)
            self.calibration_data = model_data.get('calibration_data', [])
            self.last_calibration_time = model_data.get('last_calibration_time')
        except Exception:
            pass

# Global calibrator instance
confidence_calibrator = ConfidenceCalibrator(filepath="data/confidence_calibration.pkl")