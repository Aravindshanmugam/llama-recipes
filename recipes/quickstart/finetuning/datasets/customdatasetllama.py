# Copyright (c) Meta Platforms, Inc. and affiliates.
# This software may be used and distributed according to the terms of the Llama 2 Community License Agreement.

# For dataset details visit: https://huggingface.co/datasets/samsum

import copy
import datasets
import itertools


B_INST, E_INST = "[INST]", "[/INST]"

def tokenize_dialog(dialog, tokenizer):
    if tokenizer.vocab_size >= 128000:
        dialog_tokens = tokenizer.apply_chat_template(dialog)
        dialog_tokens = dialog_tokens[:-4] # Remove generation prompt <|start_header_id|>assistant<|end_header_id|>\n\n
        eot_indices = [i for i,n in enumerate(dialog_tokens) if n == 128009]
        labels = copy.copy(dialog_tokens)
        last_idx = 0
        for n, idx in enumerate(eot_indices):
            if n % 2 == 1:
                last_idx = idx
            else:
                labels[last_idx:idx+1] = [-100] * (idx-last_idx+1)

        dialog_tokens = [dialog_tokens]
        labels_tokens = [labels]
    else:
        prompt_tokens = [tokenizer.encode(f"{tokenizer.bos_token}{B_INST} {(prompt['content']).strip()} {E_INST}", add_special_tokens=False) for prompt in dialog[::2]]
        answer_tokens = [tokenizer.encode(f"{answer['content'].strip()} {tokenizer.eos_token}", add_special_tokens=False) for answer in dialog[1::2]]
        dialog_tokens = list(itertools.chain.from_iterable(zip(prompt_tokens, answer_tokens)))

        #Add labels, convert prompt token to -100 in order to ignore in loss function
        labels_tokens = [len(c)*[-100,] if i % 2 == 0 else c for i,c in enumerate(dialog_tokens)]

    combined_tokens = {
        "input_ids": list(itertools.chain(*(t for t in dialog_tokens))),
        "labels": list(itertools.chain(*(t for t in labels_tokens))),
    }

    return dict(combined_tokens, attention_mask=[1]*len(combined_tokens["input_ids"]))


def get_custom_dataset(dataset_config, tokenizer, split):
    # dataset = datasets.load_dataset("rvind2508/Appian_postprocessed-1.2", split=split)
    # print(list(dataset.features))
    # dataset = dataset.map(lambda sample: {
    #     "goal": sample["goal"],
    #     "parent_id": sample["ruletype"],
    #     "code": sample["code"],
    #     },
    #     batched=True,
    #     remove_columns=list(dataset.features),)

    nodes = {}

    messages = {}
    root_ids = []

    # for data in dataset:
    #     if data["parent_id"]:
    #         nodes[data["parent_id"]] = nodes.get(data["parent_id"], []) + [data["goal"]]
    #     else:
    #         root_ids.append(data["goal"])
    #     messages[data["goal"]]=data["code"]
    #     print(messages)
    # def follow(thread, current_id):
    #     thread = copy.copy(thread) + [messages[current_id]]
    #     if current_id in nodes:
    #         new_threads = []
    #         for next_id in nodes[current_id]:
    #             new_threads += follow(thread, next_id)
    #         return new_threads
    #     else:
    #         return [thread]
    #
    # def get_threads_from_root(root_id):
    #     all_threads = []
    #     thread = [messages[root_id]]
    #     for cid in nodes[root_id]:
    #         all_threads += follow(thread, cid)
    #     return all_threads

    # dataset = dataset.filter(lambda x: x["goal"] in root_ids)
    # dataset = dataset.map(lambda x: {"thread": get_threads_from_root(x["goal"])}, remove_columns=list(dataset.features))
    # dataset = dataset.map(lambda x: {"thread": [i for row in x["thread"] for i in row]}, batched=True)

    def to_dialog(thread):
        dialog = []
        for i, content in enumerate(thread):
            dialog.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": content['content'],
            })
        return {"dialog": dialog}

    dataset = datasets.load_dataset("rvind2508/Datasetfromsolution_extracted_formated", split=split)
    dataset = dataset.map(lambda x: to_dialog(x["messages"]), remove_columns=list(dataset.features))
    dataset = dataset.map(lambda x: tokenize_dialog(x["dialog"], tokenizer), remove_columns=list(dataset.features))

    return dataset

# print(get_custom_dataset('','128000','train'))
