# 检测到的手对象的数据结构模型(官方 API)
results.multi_hand_landmarks = [hand0, hand1] 
"results" = hands.process(rgb_frame) # 获得处理后的图像数据
|
└── multi_hand_landmarks（手对象的列表 "landmarks_list"）
    ├── "hand_landmarks"(第1只手,hand0)
    │   └── landmark
    │       ├── 第0个点
    │       ├── 第1个点
    │       ├── ...
    │       └── 第20个点
    └── hand_landmarks(第2只手,hand1)
        └── landmark
            ├── 第0个点
            ├── ...
            └── 第20个点

# 存储方式
    [  -->  外层 "all_hand"
         [[id, x, y], ...],   # 第1只手 all_hands[0]  -->  内层 "lm_list"
         [[id, x, y], ...]    # 第2只手 all_hands[1]
    ]

# 手部关键点编号结构
手腕(0)
0：手腕
拇指(1~4) : 从下往上增加
1：拇指根部附近
4：拇指尖

食指(5~8)
5：食指根部
8：食指尖

中指(9~12)
9：中指根部
12：中指尖

无名指(13~16)
13：无名指根部
16：无名指尖

小指(17~20)
17：小指根部
20：小指尖