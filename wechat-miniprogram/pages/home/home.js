// 首页：设置玩家人数和名字，开始游戏
const { initGame, prepareRound } = require('../../utils/gameLogic');

Page({
  data: {
    numPlayers: 3,                              // 玩家人数（3或4）
    playerNames: ['玩家1', '玩家2', '玩家3', '玩家4'], // 玩家名字输入框
  },

  // 切换玩家人数
  setCount(e) {
    const count = e.currentTarget.dataset.count;
    this.setData({ numPlayers: count });
  },

  // 修改玩家名字
  setName(e) {
    const idx = e.currentTarget.dataset.idx;
    const val = e.detail.value || `玩家${idx + 1}`;
    const names = [...this.data.playerNames];
    names[idx] = val;
    this.setData({ playerNames: names });
  },

  // 点击"开始游戏"
  startGame() {
    const { numPlayers, playerNames } = this.data;
    const names = playerNames.slice(0, numPlayers);

    // 初始化游戏状态
    let state = initGame(names);
    state = prepareRound(state);

    // 将游戏状态存入全局，传递给游戏页面
    const app = getApp();
    app.globalData.gameState = state;

    // 跳转到游戏页
    wx.navigateTo({ url: '/pages/game/game' });
  }
});
