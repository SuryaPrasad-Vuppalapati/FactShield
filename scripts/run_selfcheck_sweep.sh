#!/bin/bash

for model in bart t5 pegasus; do
    for dataset in cnndm xsum faithbench; do
        echo "========================================"
        echo "Running selfcheck: $model × $dataset"
        echo "========================================"
        python3 -m pipelines.selfcheck.run --model_name $model --dataset $dataset --K 5 --score_mode all
    done
done

echo "Selfcheck sweep complete"