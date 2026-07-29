from app.experimental.similarity import calculate_similarity


def build_playlist(
    start_track,
    candidates,
):
    playlist = [start_track]

    remaining = candidates.copy()

    current = start_track

    while remaining:

        best = max(
            remaining,
            key=lambda track: calculate_similarity(
                current,
                track,
            ),
        )

        playlist.append(best)

        remaining.remove(best)

        current = best

    return playlist