def get_finger_state(hand):
    """
    输入一只手的21个关键点:
    hand = [[id, x, y], ...]
    返回五指状态:
    [thumb, index, middle, ring, pinky]
    1 表示伸出，0 表示弯曲
    """
    fingers = [0, 0, 0, 0, 0]

    if not hand or len(hand) != 21:
        return fingers

    # 拇指（先做简化版本，后续再优化左右手判断）
    if hand[4][1] > hand[3][1]:
        fingers[0] = 1

    # 食指
    if hand[8][2] < hand[6][2]:
        fingers[1] = 1

    # 中指
    if hand[12][2] < hand[10][2]:
        fingers[2] = 1

    # 无名指
    if hand[16][2] < hand[14][2]:
        fingers[3] = 1

    # 小指
    if hand[20][2] < hand[18][2]:
        fingers[4] = 1

    return fingers