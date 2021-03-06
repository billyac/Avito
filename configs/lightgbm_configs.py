from hyperopt import hp

lightgbm_config_feature_list = [
    'user_id',
    'region',
    'city',
    'parent_category_name',
    'category_name',
    'param_1',
    'param_2',
    'param_3',
    'price',
    'item_seq_number',
    # 'activation_date',
    'user_type',
    'image_top_1',
    'has_image',
    'title_len',
    'title_wc',
    'desc_len',
    'desc_wc',
    'listings_per_user',
    'listings_per_city_date',
    'price_city_date_mean_max',
]
lightgbm_config = {
    'features': lightgbm_config_feature_list,
    'folds':5,
    'model': 'lightgbm',
    'model_params': {
        'boosting_type': 'gbdt',
        'categorical_feature': '0,1,2,3,4,5,6,7,10,11',
        'learning_rate': 0.15003406796297156,
        'max_bin': 110,
        'metric': 'mse',
        'min_data': 180,
        'min_hessian': 0.07644471992150681,
        'num_boost_round': 300,
        'num_leaves': 145,
        'objective': 'regression',
        'sub_feature': 0.36665200573883905,
        'verbose': -1
    },
    'tune_params': {
        'param_space': {
            'features': lightgbm_config_feature_list,
            'model': 'lightgbm',
            'folds': 5,
            'model_params': {
                'learning_rate': hp.loguniform('learning_rate', -2, 0),
                'boosting_type': 'gbdt',
                'categorical_feature': '0,1,2,3,4,5,6,7,10,11',
                'objective': 'regression',
                'metric': hp.choice('metric', ['mae', 'mse']),
                'sub_feature': hp.uniform('sub_feature', 0.1, 0.5),
                'num_leaves': hp.choice('num_leaves', list(range(10, 151, 15))),
                'min_data': hp.choice('min_data', list(range(150, 301, 15))),
                'min_hessian': hp.loguniform('min_hessian', -3, 1),
                'num_boost_round': hp.choice('num_boost_round', [200, 300, 500]),
                'max_bin': hp.choice('max_bin', list(range(50, 151, 10))),
                # 'bagging_fraction': hp.uniform('bagging_fraction', 0.5, 1),
                # 'bagging_freq': hp.choice('bagging_freq', list(range(0, 100, 10))),
                'verbose': -1
            },
        },
        'max_evals': 80
    }
}
