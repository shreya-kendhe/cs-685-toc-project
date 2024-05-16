import os
import json

def save_results(args, data, preds, outputs):
    preds_w_ids = {}
    outputs_w_ids = {}
    for idx in range(len(data)):
        d = data[idx]
        if idx >= len(preds):
            break
        
        preds_w_ids[d['ID']] = preds[idx]
        outputs_w_ids[d['ID']] = outputs[idx]
        
    os.makedirs(args.output_dir, exist_ok=True)
    
    with open(os.path.join(args.output_dir, args.prefix + "preds.json"), 'w') as f:
        json.dump(preds_w_ids, f)
        
    with open(os.path.join(args.output_dir, args.prefix + "outputs.json"), 'w') as f:
        json.dump(outputs_w_ids, f)
        

