#!/bin/bash

for model in bart t5 pegasus; do
    for dataset in cnndm xsum faithbench; do
        echo "========================================"
        echo "Running entailment: $model × $dataset"
        echo "========================================"
        python3 -m pipelines.entailment.run --model_name $model --dataset $dataset --methods minicheck
    done
done

echo "Entailment sweep complete"