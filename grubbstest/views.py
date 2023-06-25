from .grubbstest import grubbstest_bp
from flask import Flask, render_template, request, redirect, url_for
import numpy as np
import copy
from scipy.stats import t # add this line

def grubbs_test(data, alpha=0.05):
  N = len(data)  # The number of data points
  std_dev = np.std(data)  # The standard deviation of the data
  avg_y = np.mean(data)  # The mean of the data
  abs_val_minus_avg = abs(
    data - avg_y)  # The absolute deviation of each point from the mean
  max_of_deviations = max(abs_val_minus_avg)  # The maximum absolute deviation
  max_ind = np.argmax(
    abs_val_minus_avg)  # The index of the maximum absolute deviation

  # Compute the test statistic (Grubbs' statistic)
  Gcal = max_of_deviations / std_dev

  # Compute the critical value
  t_value = t.ppf(1 - alpha / (2 * N), N - 2)
  Gcrit = ((N - 1) * np.sqrt(np.square(t_value))) / (
    np.sqrt(N) * np.sqrt(N - 2 + np.square(t_value)))

  # If the test statistic is greater than the critical value, we have found an outlier
  if Gcal > Gcrit:
    return True, max_ind

  # Otherwise, there is no outlier
  else:
    return False, None

def run_grubbs_test(data):
  outliers = []
  outliers_indices = []
  data_copy = copy.deepcopy(data)
  while True:
    is_outlier, ind = grubbs_test(data_copy)
    if is_outlier:
      outliers.append(data_copy[ind])
      outliers_indices.append(np.where(data == data_copy[ind])[0][0])
      data_copy = np.delete(data_copy, ind)
    else:
      break
  return outliers, outliers_indices

@grubbstest_bp.route('/', methods=['GET', 'POST'])
def grubbstest():
  data = None
  outliers = None
  outliers_indices = None

  if request.method == 'POST':
    # Get data from form
    data = request.form.get('data')
    # Convert data to numpy array
    data = np.fromstring(data, sep=',')
    # Run Grubbs' test
    outliers, outliers_indices = run_grubbs_test(data)

  return render_template('grubbstest.html',
                         data=list(data) if data is not None else None,
                         outliers=outliers,
                         outliers_indices=outliers_indices)
