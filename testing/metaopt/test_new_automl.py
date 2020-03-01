import numpy as np
from sklearn import linear_model
from sklearn.metrics import mean_squared_error

from neuraxle.base import ExecutionContext
from neuraxle.hyperparams.distributions import FixedHyperparameter
from neuraxle.hyperparams.space import HyperparameterSpace
from neuraxle.metaopt.auto_ml import RandomSearchHyperparameterOptimizer
from neuraxle.metaopt.new_automl import AutoML, InMemoryHyperparamsRepository, EarlyStoppingCallback
from neuraxle.metaopt.random import ValidationSplitWrapper, KFoldCrossValidationWrapper, average_kfold_scores
from neuraxle.pipeline import Pipeline
from neuraxle.steps.misc import FitTransformCallbackStep
from neuraxle.steps.numpy import MultiplyByN, NumpyReshape


def test_automl_with_validation_split_wrapper(tmpdir):
    # Given
    hp_repository = InMemoryHyperparamsRepository(cache_folder=str(tmpdir))
    auto_ml = AutoML(
        pipeline=Pipeline([
            MultiplyByN(2).set_hyperparams_space(HyperparameterSpace({
                'multiply_by': FixedHyperparameter(2)
            })),
            NumpyReshape(shape=(-1, 1)),
            linear_model.LinearRegression()
        ]),
        validation_technique=ValidationSplitWrapper(test_size=0.2, scoring_function=mean_squared_error),
        hyperparams_optimizer=RandomSearchHyperparameterOptimizer(),
        hyperparams_repository=hp_repository,
        scoring_function=mean_squared_error,
        refit_scoring_function=mean_squared_error,
        n_trial=1,
        metrics={'mse': mean_squared_error},
        epochs=2,
        callbacks=[]
    )

    # When
    data_inputs = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expected_outputs = data_inputs * 2
    auto_ml.fit(data_inputs=data_inputs, expected_outputs=expected_outputs)

    # Then
    p = _get_saved_model(hp_repository)
    outputs = p.transform(data_inputs)
    mse = mean_squared_error(expected_outputs, outputs)

    assert mse < 500


def test_automl_with_validation_split_wrapper(tmpdir):
    # Given
    hp_repository = HyperparamsRepository(cache_folder=str(tmpdir))
    auto_ml = AutoML(
        pipeline=Pipeline([
            MultiplyByN(2).set_hyperparams_space(HyperparameterSpace({
                'multiply_by': FixedHyperparameter(2)
            })),
            NumpyReshape(shape=(-1, 1)),
            linear_model.LinearRegression()
        ]),
        validation_technique=ValidationSplitWrapper(test_size=0.2, scoring_function=mean_squared_error),
        hyperparams_optimizer=RandomSearchHyperparameterOptimizer(),
        hyperparams_repository=hp_repository,
        scoring_function=mean_squared_error,
        refit_scoring_function=mean_squared_error,
        n_trial=1,
        metrics={'mse': mean_squared_error},
        epochs=2,
        callbacks=[]
    )

    # When
    data_inputs = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expected_outputs = data_inputs * 2
    auto_ml.fit(data_inputs=data_inputs, expected_outputs=expected_outputs)

    # Then
    p = _get_saved_model(hp_repository)
    outputs = p.transform(data_inputs)
    mse = mean_squared_error(expected_outputs, outputs)

    assert mse < 500


def test_automl_early_stopping_callback(tmpdir):
    # Given
    hp_repository = InMemoryHyperparamsRepository(cache_folder=str(tmpdir))
    n_epochs = 60
    auto_ml = AutoML(
        pipeline=Pipeline([
            FitTransformCallbackStep().set_name('callback'),
            MultiplyByN(2).set_hyperparams_space(HyperparameterSpace({
                'multiply_by': FixedHyperparameter(2)
            })),
            NumpyReshape(shape=(-1, 1)),
            linear_model.LinearRegression()
        ]),
        validation_technique=ValidationSplitWrapper(test_size=0.2, scoring_function=mean_squared_error),
        hyperparams_optimizer=RandomSearchHyperparameterOptimizer(),
        hyperparams_repository=hp_repository,
        scoring_function=mean_squared_error,
        refit_scoring_function=mean_squared_error,
        n_trial=1,
        metrics={'mse': mean_squared_error},
        epochs=n_epochs,
        callbacks=[EarlyStoppingCallback(n_epochs_without_improvement=3, higher_score_is_better=False)],
        refit_trial=False
    )

    # When
    data_inputs = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expected_outputs = data_inputs * 2
    auto_ml.fit(data_inputs=data_inputs, expected_outputs=expected_outputs)

    # Then
    p = _get_saved_model(hp_repository)
    callback_step = p.get_step_by_name('callback')

    assert len(callback_step.fit_callback_function.data) < n_epochs


def test_automl_with_kfold(tmpdir):
    # Given
    hp_repository = InMemoryHyperparamsRepository(cache_folder=str(tmpdir))
    auto_ml = AutoML(
        pipeline=Pipeline([
            MultiplyByN(2).set_hyperparams_space(HyperparameterSpace({
                'multiply_by': FixedHyperparameter(2)
            })),
            NumpyReshape(shape=(-1, 1)),
            linear_model.LinearRegression()
        ]),
        validation_technique=KFoldCrossValidationWrapper(
            k_fold=2,
            scoring_function=average_kfold_scores(mean_squared_error),
            split_data_container_during_fit=False,
            predict_after_fit=False
        ),
        hyperparams_optimizer=RandomSearchHyperparameterOptimizer(),
        hyperparams_repository=hp_repository,
        scoring_function=average_kfold_scores(mean_squared_error),
        refit_scoring_function=mean_squared_error,
        n_trial=1,
        metrics={'mse': average_kfold_scores(mean_squared_error)},
        epochs=10,
        callbacks=[]
    )

    data_inputs = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expected_outputs = data_inputs * 4

    # When
    auto_ml.fit(data_inputs=data_inputs, expected_outputs=expected_outputs)

    # Then
    p = _get_saved_model(hp_repository)
    outputs = p.transform(data_inputs)
    mse = mean_squared_error(expected_outputs, outputs)

    assert mse < 500


def _get_saved_model(hp_repository):
    hp_dict = {
        'MultiplyByN__multiply_by': 2,
        'LinearRegression__copy_X': True,
        'LinearRegression__fit_intercept': True,
        'LinearRegression__n_jobs': None,
        'LinearRegression__normalize': False
    }
    trial_hash = hp_repository._get_trial_hash(hp_dict)
    p = ExecutionContext(str(hp_repository.cache_folder)).load(trial_hash)
    return p
