import numpy as np
from scipy.special import expit
from scipy import stats
import pandas as pd
import matplotlib.pyplot as plt
from enum import Enum

class Ball(Enum):
    RED = 0
    BLUE = 1

class BucketColour(Enum):
    RED = 0
    BLUE = 1

class Algorithm(Enum):
    REGULAR = 0
    MOMENTUM = 1
    ADAM = 2

class ScoreFunction(Enum):
    LOG = 0
    QUADRATIC = 1

class PredictionMarket:

    def __init__(self, no, prior_red):
        self.no = no
        self.init_prediction = [prior_red, 1 - prior_red]
        self.current_prediction = self.init_prediction.copy()
        self.previous_prediction = self.current_prediction.copy()

    def report(self, prediction):
        assert sum(prediction) == 1, print('Probabilities not sum to one!', prediction)
        # Record the contract if multiple traders.
        self.previous_prediction = self.current_prediction.copy()
        self.current_prediction = prediction.copy()

    def log_resolve(self, materialised_index):
        scores = np.log(self.current_prediction) - np.log(self.previous_prediction)
        return scores[materialised_index]

    def brier_resolve(self, materialised_index):
        current_scores = self.current_prediction[materialised_index] - np.sum(np.square(self.current_prediction))/2
        previous_scores = self.previous_prediction[materialised_index] - np.sum(np.square(self.previous_prediction))/2
        return current_scores - previous_scores

    def resolve(self, score_func, materialised_index):
        if score_func == ScoreFunction.LOG:
            return self.log_resolve(materialised_index)
        elif score_func == ScoreFunction.QUADRATIC:
            return self.brier_resolve(materialised_index)
        else:
            raise ValueError('The score function does not exist.')




class DecisionMarket:

    def __init__(self, action_num, prior_red):
        self.conditional_market_num = action_num
        self.conditional_market_list = list(PredictionMarket(no, prior_red) for no in range(self.conditional_market_num))

    def report(self, prediction, conditional_market_no):
        self.conditional_market_list[conditional_market_no].report(prediction)



    def log_resolve(self, conditional_market_no, materialised_index):
        return self.conditional_market_list[conditional_market_no].log_resolve(materialised_index)

    def read_current_pred(self):
        current_price_list = list(pm.current_prediction[0] for pm in self.conditional_market_list)


class Bucket:
    def __init__(self, no, prior_red, pr_red_ball_red_bucket, pr_red_ball_blue_bucket):
        assert prior_red >= 0, 'Prior can not be negative!'
        assert prior_red <= 1, 'Prior can not greater than one!'
        assert pr_red_ball_red_bucket >= 0, 'Prior can not be negative!'
        assert pr_red_ball_red_bucket <= 1, 'Prior can not greater than one!'
        assert pr_red_ball_blue_bucket >= 0, 'Prior can not be negative!'
        assert pr_red_ball_blue_bucket <= 1, 'Prior can not greater than one!'

        self.no = no
        self.prior_red = prior_red
        self.pr_red_ball_red_bucket = pr_red_ball_red_bucket
        self.pr_red_ball_blue_bucket = pr_red_ball_blue_bucket
        self.colour = np.random.choice([BucketColour.RED, BucketColour.BLUE], p=(self.prior_red, 1 - self.prior_red))

    def signal(self):
        if self.colour == BucketColour.RED:
            ball_distribution = (self.pr_red_ball_red_bucket, 1 - self.pr_red_ball_red_bucket)
        elif self.colour == BucketColour.BLUE:
            ball_distribution = (self.pr_red_ball_blue_bucket, 1 - self.pr_red_ball_blue_bucket)
        else:
            raise ValueError('Bucket colour incorrect, colour is ' + str(self.colour.name))
        return np.random.choice([Ball.RED, Ball.BLUE], p=ball_distribution)

class MultiBuckets:
    def __init__(self, bucket_num, prior_red, pr_red_ball_red_bucket, pr_red_ball_blue_bucket):
        self.prior_red = prior_red
        self.pr_red_ball_red_bucket = pr_red_ball_red_bucket
        self.pr_red_ball_blue_bucket = pr_red_ball_blue_bucket
        self.bucket_list = []
        for no in range(bucket_num):
            self.bucket_list.append(Bucket(no, prior_red, pr_red_ball_red_bucket, pr_red_ball_blue_bucket))

    def signal(self):
        # Randomly select a bucket
        bucket = np.random.choice(self.bucket_list)
        return bucket.no, bucket.signal()

class Explorer:
    def __init__(self, feature_shape, learning=True, init_learning_rate=0.001, min_std=0.3):
        self.mean = 0
        self.std = 1.0
        self.theta_std = np.zeros(feature_shape)
        self.init_learning_rate = init_learning_rate
        self.learning_rate = init_learning_rate
        self.h = 0
        self.learning = learning
        self.min_std = min_std

    def set_parameters(self, mean, std=1.0):
        self.mean = mean
        self.std = std

    def learning_rate_decay(self, epoch, decay_rate):
        self.learning_rate = 1 / (1 + decay_rate * epoch) * self.init_learning_rate
        return self.learning_rate

    def report(self, x):
        x = np.array(x)
        if self.learning:
            [self.std] = np.exp(np.dot(self.theta_std, x.T))
            if self.std < self.min_std:
                self.std = self.min_std
        self.h = np.random.normal(loc=self.mean, scale=self.std)
        return self.h

    def update(self, reward, x):
        if self.learning:
            gradient_std = reward * np.array([x]) * ((self.h - self.mean) ** 2 / self.std ** 2 - 1)
            self.theta_std += self.learning_rate * gradient_std


def analytical_best_report_ru_rs(pr_ru, pr_rs_ru, pr_rs_bu):
    """
    :param pr_ru: float
        Prior probability of red urn
    :param pr_rs_ru: float
        Conditional probability of red ball signal given red urn
    :param pr_rs_bu: float
        conditional probability of red ball signal given blue urn
    :return: float
        Conditional probability of red urn given red ball signal
    """
    joint_distribution_ru_rs = pr_ru * pr_rs_ru
    joint_distribution_bu_rs = (1 - pr_ru) * pr_rs_bu
    return joint_distribution_ru_rs / (joint_distribution_ru_rs + joint_distribution_bu_rs)


def analytical_best_report_ru_bs(pr_ru, pr_bs_ru, pr_bs_bu):
    """
    :param pr_ru: float
        Prior probability of red urn
    :param pr_bs_ru: float
        Conditional probability of blue ball signal given red urn
    :param pr_bs_bu: float
        conditional probability of blue ball signal given blue urn
    :return: float
        Conditional probability of red urn given blue ball signal
    """

    joint_distribution_ru_rs = pr_ru * pr_bs_ru
    joint_distribution_bu_rs = (1 - pr_ru) * pr_bs_bu
    return joint_distribution_ru_rs / (joint_distribution_ru_rs + joint_distribution_bu_rs)


def expected_log_reward_red_ball(actual_pr_ru_rs, estimated_pr_ru_rs, pr_ru):
    """
    This function compute the expected logarithmic reward given a red ball signal
    :param actual_pr_ru_rs: float
        Ground truth probability of conditional probability of red urn given a red ball signal
    :param estimated_pr_ru_rs: float
        Estimated probability of conditional probability of red urn given a red ball signal
    :param pr_ru: float
        Prior probability of a red urn
    :return: float
        expected logarithmic reward given red signal
    """
    return actual_pr_ru_rs * (np.log(estimated_pr_ru_rs) - np.log(pr_ru)) + (1 - actual_pr_ru_rs) * (
            np.log(1 - estimated_pr_ru_rs) - np.log(1 - pr_ru))

def expected_quodratic_reward_red_ball(actual_pr_ru_rs, estimated_pr_ru_rs, pr_ru):
    """
    This function compute the expected logarithmic reward given a red ball signal
    :param actual_pr_ru_rs: float
        Ground truth probability of conditional probability of red urn given a red ball signal
    :param estimated_pr_ru_rs: float
        Estimated probability of conditional probability of red urn given a red ball signal
    :param pr_ru: float
        Prior probability of a red urn
    :return: float
        expected logarithmic reward given red signal
    """
    return actual_pr_ru_rs * (np.log(estimated_pr_ru_rs) - np.log(pr_ru)) + (1 - actual_pr_ru_rs) * (
            np.log(1 - estimated_pr_ru_rs) - np.log(1 - pr_ru))


def expected_log_reward_blue_ball(actual_pr_ru_bs, estimated_pr_ru_bs, pr_ru):
    """
    This function compute the expected logarithmic reward given a blue ball signal
    :param actual_pr_ru_bs: float
        Ground truth probability of conditional probability of red urn given a blue ball signal
    :param estimated_pr_ru_bs: float
        Estimated probability of conditional probability of red urn given a blue ball signal
    :param pr_ru: float
        Prior probability of a red urn
    :return: float
        expected logarithmic reward given red signal
    """
    return actual_pr_ru_bs * (np.log(estimated_pr_ru_bs) - np.log(pr_ru)) + (1 - actual_pr_ru_bs) * (
            np.log(1 - estimated_pr_ru_bs) - np.log(1 - pr_ru))


# TODO: How to compute the regret for second agent?
# def compute_regret(signal, pi, prior_red, pr_red_ball_red_bucket, pr_red_ball_blue_bucket):
#     if signal == 'red':
#         actual_pr_ru_S = analytical_best_report_ru_rs(pr_ru=prior_red, pr_rs_ru=pr_red_ball_red_bucket,
#                                                       pr_rs_bu=pr_red_ball_blue_bucket)
#         expected_log_reward = expected_log_reward_red_ball(actual_pr_ru_rs=actual_pr_ru_S, estimated_pr_ru_rs=pi,
#                                                            pr_ru=prior_red)
#         max_expected_log_reward = expected_log_reward_red_ball(actual_pr_ru_rs=actual_pr_ru_S,
#                                                                estimated_pr_ru_rs=actual_pr_ru_S, pr_ru=prior_red)
#     else:
#         actual_pr_ru_S = analytical_best_report_ru_bs(pr_ru=prior_red, pr_bs_ru=1 - pr_red_ball_red_bucket,
#                                                       pr_bs_bu=1 - pr_red_ball_blue_bucket)
#         expected_log_reward = expected_log_reward_blue_ball(actual_pr_ru_bs=actual_pr_ru_S, estimated_pr_ru_bs=pi,
#                                                             pr_ru=prior_red)
#         max_expected_log_reward = expected_log_reward_blue_ball(actual_pr_ru_bs=actual_pr_ru_S,
#                                                                 estimated_pr_ru_bs=actual_pr_ru_S, pr_ru=prior_red)
#     return max_expected_log_reward - expected_log_reward

def no_outlier_array(points, thresh=3):
    z = np.abs(stats.zscore(points))
    z = z.reshape(-1)
    return points[z < thresh]


def no_outlier_df(df, thresh=3):
    return df[(np.abs(stats.zscore(df)) < thresh).all(axis=1)]


def one_hot_encode(feature):
    if feature == 'red':
        return [1, 0]
    else:
        return [0, 1]


def one_hot_decode(one_hot_feature):
    if one_hot_feature == [1, 0]:
        return 'red'
    else:
        return 'blue'


def gradients_box_plot(df, bins, col_name, color, ax):
    _df = df.copy()
    _df['bin'] = pd.cut(_df.index.to_series(), bins=bins, include_lowest=True)

    box_list = []
    for interval in _df['bin'].unique():
        box_list.append(_df.loc[_df['bin'] == interval, col_name].values)
    bplot = ax.boxplot(box_list, patch_artist=True, notch=True, vert=True, meanline=False, zorder=-99, showmeans=True)
    left, right = ax.get_xlim()
    ax.hlines(y=0, xmin=left, xmax=right, linestyles='dashdot', zorder=-98, color='black')
    for patch in bplot['boxes']:
        patch.set_facecolor(color)
    ax.yaxis.grid(True)
    ax.set_xticklabels(labels=_df['bin'].unique(), rotation=15)
    ax.set_title(col_name)


def gradients_box_subplot(df, column_list, colour_list, axs):
    for col_name, ax, colour in zip(column_list, axs, colour_list):
        gradients_box_plot(df, bins=10, col_name=col_name, color=colour, ax=ax)


bucket_colour_to_num = {'red_bucket': 0, 'blue_bucket': 1}
