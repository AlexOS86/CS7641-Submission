#!/bin/sh

# Replace 'X' below with the optimal values found
# If you want to first generate data and updated datasets, remove the "--skiprerun" flags below

python run_experiment.py --ica --dataset1 --dim 30 --skiprerun --verbose --threads -1 --seed 22 > ica-dataset1-clustering.log 2>&1
# the knee for max was estiamted at 30, this is not the true max but is significatntly above 3

python run_experiment.py --ica --dataset2 --dim 25 --skiprerun --verbose --threads -1 --seed 22 > ica-dataset2-clustering.log 2>&1
# 25 gets above normal gaussian but still allows for some type of dim redicution

python run_experiment.py --pca --dataset1 --dim 3 --skiprerun --verbose --threads -1 --seed 22 > pca-dataset1-clustering.log 2>&1


python run_experiment.py --pca --dataset2 --dim 5 --skiprerun --verbose --threads -1 --seed 22 > pca-dataset2-clustering.log 2>&1
# the knee from this looked right to me

python run_experiment.py --rp  --dataset1 --dim 8 --skiprerun --verbose --threads -1 --seed 22 > rp-dataset1-clustering.log  2>&1
# the two predictors agreed
python run_experiment.py --rp  --dataset2 --dim 10 --skiprerun --verbose --threads -1 --seed 22 > rp-dataset2-clustering.log  2>&1
# split the different between the two predictors

python run_experiment.py --rf  --dataset1 --dim 11 --skiprerun --verbose --threads -1 --seed 22 > rf-dataset1-clustering.log  2>&1
# this was several below the one from the graphic, but seemed like a better knee point
python run_experiment.py --rf  --dataset2 --dim 4 --skiprerun --verbose --threads -1 --seed 22 > rf-dataset2-clustering.log  2>&1
#same applies for phishing

#python run_experiment.py --svd --dataset1 --dim X --skiprerun --verbose --threads -1 > svd-dataset1-clustering.log 2>&1
#python run_experiment.py --svd --dataset2 --dim X --skiprerun --verbose --threads -1 > svd-dataset2-clustering.log 2>&1
