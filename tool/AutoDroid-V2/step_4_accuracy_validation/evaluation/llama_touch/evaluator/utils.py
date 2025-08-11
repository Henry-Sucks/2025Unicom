import pandas as pd

def get_instructions_episodes(instruction_fp):
    instructions = pd.read_csv(instruction_fp, sep='\t')
    episodes = []
    
    for _, row in instructions.iterrows():
        episodes.append(str(row['episode']))

    return episodes