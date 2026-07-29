def detect_phrases(beat_times):

    phrases = []

    beats = beat_times["beats"]

    BAR = 4
    PHRASE = 32

    for i in range(0, len(beats), PHRASE):

        if i + PHRASE < len(beats):

            phrases.append({

                "start": beats[i],

                "end": beats[i + PHRASE],

                "bars": 8

            })

    return phrases