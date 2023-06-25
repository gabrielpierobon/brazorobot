from .grubbstest import grubbstest_bp
from flask import Flask, render_template, request, redirect, url_for
import numpy as np
import pandas as pd
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
    z_scores = (data_copy - np.mean(data_copy)) / np.std(data_copy)  # calculate z-scores
    z_scores_list = [round(z, 2) for z in z_scores.tolist()]  # convert to list and round to 2 decimals
    initial_data_indices = list(range(len(data)))  # Record the initial indices

    while True:
        is_outlier, ind = grubbs_test(data_copy)
        if is_outlier:
            outliers.append(data_copy[ind])
            outliers_indices.append(initial_data_indices.pop(ind))
            data_copy = np.delete(data_copy, ind)
        else:
            break

    print(outliers)
    print(outliers_indices)
    return outliers, outliers_indices, z_scores_list, initial_data_indices

def get_frequency_data(data):
    df = pd.DataFrame(data, columns=['Data'])
    frequency_data = df['Data'].value_counts().sort_index().reset_index().values.tolist()
    return frequency_data

@grubbstest_bp.route('/', methods=['GET', 'POST'])
def grubbstest():
    data = None
    outliers = None
    outliers_indices = None
    data_for_chart = None
    outliers_for_chart = None
    z_scores = None
    distribution_data = None

    if request.method == 'POST':
        # Get data from form
        data_str = request.form.get('data')
        if data_str:  # only process if data_str is not empty
            # Convert data to numpy array
            data = np.fromstring(data_str, sep=',')
            # Run Grubbs' test
            outliers, outliers_indices, z_scores, data_indices = run_grubbs_test(data)

            # Prepare data for Chart.js
            data_for_chart = [{'x': int(i), 'y': float(y)} for i, y in zip(data_indices, data[data_indices])]
            outliers_for_chart = [{'x': int(i), 'y': float(y)} for i, y in zip(outliers_indices, outliers)]
            print(outliers_for_chart)

            distribution_data = get_frequency_data(data)

    return render_template('grubbstest.html',
                           data=list(data) if data is not None else None,
                           outliers=outliers,
                           outliers_indices=outliers_indices,
                           data_for_chart=data_for_chart,
                           outliers_for_chart=outliers_for_chart,
                           first_z_scores=z_scores,
                           distribution_data=distribution_data)
