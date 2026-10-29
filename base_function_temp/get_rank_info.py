from ranks_config import RANK_TIERS


def get_rank_info(current_elo, current_rank_id=None):
    # (Ton code ici...)
    strict_rank = None
    for tier in reversed(RANK_TIERS):
        if current_elo >= tier["threshold"]:
            strict_rank = tier
            break

    if current_rank_id is None:
        return strict_rank

    if strict_rank["id"] < current_rank_id:
        current_tier = next(t for t in RANK_TIERS if t["id"] == current_rank_id)
        if current_elo >= (current_tier["threshold"] - 25):
            return current_tier
        else:
            return strict_rank
    else:
        return strict_rank
