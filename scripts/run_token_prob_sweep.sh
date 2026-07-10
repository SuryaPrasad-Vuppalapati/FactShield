#!/bin/bash

for model in bart t5 pegasus; do
    for dataset in cnndm xsum faithbench; do
        echo "========================================"
        echo "Running token_prob: $model × $dataset"
        echo "========================================"
        python3 -m pipelines.token_prob.run --model_name $model --dataset $dataset
    done
done

echo "Token prob sweep complete"