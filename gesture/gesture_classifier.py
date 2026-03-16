def classify_gesture(fingers):
    """
    根据五指状态分类手势
    """
    if fingers == [0, 0, 0, 0, 0]:
        return "FIST"

    if fingers == [1, 1, 1, 1, 1]:
        return "OPEN_HAND"

    if fingers == [0, 1, 0, 0, 0]:
        return "INDEX_UP"

    if fingers == [0, 1, 1, 0, 0]:
        return "V_SIGN"

    return "UNKNOWN"