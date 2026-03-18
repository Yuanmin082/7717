/**
 * 游戏主页面
 *
 * 阶段（phase）说明：
 *   draw    - 抽牌阶段（第2~4轮，每人从牌堆抽2张）
 *   select  - 选牌阶段（每人轮流查看手牌、选2张，选完后传手机）
 *   reveal  - 揭示阶段（所有人同时亮牌，看排名）
 *   score   - 结算阶段（显示排名和金豆变化）
 *   end     - 游戏结束（显示最终分数）
 */

const {
  getTableCardForRound,
  drawCards,
  confirmSelection,
  doReveal,
  settleScore,
  nextRound,
  initGame,
  prepareRound
} = require('../../utils/gameLogic');

Page({
  data: {
    // ===== 游戏核心状态（从全局globalData同步） =====
    phase: 'select',
    round: 1,
    players: [],
    tableCards: [],
    rankings: [],
    deck: [],

    // ===== UI辅助状态 =====
    showHand: false,         // 是否显示当前玩家的手牌
    drawnCards: [],          // 本次抽到的牌（用于展示）
    currentSelectIdx: 0,     // 当前选牌玩家在selectOrder中的位置

    // ===== 选牌状态 =====
    handWithSelect: [],      // 当前玩家的手牌（带isSelected标记）
    selectedCount: 0,        // 已选张数

    // ===== 揭示状态 =====
    revealFaceDown: false,   // 是否揭开暗牌

    // ===== 便捷计算属性（由JS更新） =====
    currentPlayer: null,     // 当前操作的玩家对象
    tableCardForRound: null, // 本轮参照牌
    phaseLabel: '',          // 阶段描述文字
    roundLabel: '',          // 轮次描述文字
  },

  // 页面加载时读取全局游戏状态
  onLoad() {
    const app = getApp();
    this._state = app.globalData.gameState;
    this._syncToData();
  },

  // ===== 将游戏逻辑状态同步到页面data（触发UI更新） =====
  _syncToData() {
    const s = this._state;
    if (!s) return;

    // 确定当前操作的玩家
    let currentPlayerIdx = -1;
    if (s.phase === 'draw') {
      currentPlayerIdx = s.drawOrder[s.drawOrderIdx];
    } else if (s.phase === 'select') {
      currentPlayerIdx = s.selectOrder[s.selectOrderIdx];
    }
    const currentPlayer = currentPlayerIdx >= 0 ? s.players[currentPlayerIdx] : null;

    // 本轮参照牌
    const tableCardForRound = s.round <= 4 ? s.tableCards[s.round - 1] : null;

    // 阶段描述
    const phaseLabels = {
      draw: '📦 抽牌阶段',
      select: '🃏 选牌阶段',
      reveal: '👀 揭示阶段',
      score: '🏆 本轮结算',
      end: '🎉 游戏结束'
    };

    // 轮次描述
    const roundDescs = [
      '', '第1轮（参照第1张明牌）',
      '第2轮（参照第2张明牌）',
      '第3轮（参照第3张明牌）',
      '第4轮（揭示暗牌）',
      '第5轮（展示剩余手牌）'
    ];

    this.setData({
      phase: s.phase,
      round: s.round,
      players: s.players,
      tableCards: s.tableCards,
      rankings: s.rankings,
      deck: s.deck,
      currentPlayer,
      tableCardForRound,
      phaseLabel: phaseLabels[s.phase] || '',
      roundLabel: roundDescs[s.round] || '',
      revealFaceDown: s.round === 4 && s.phase === 'reveal',
      // 重置一些UI状态
      showHand: false,
      drawnCards: [],
      handWithSelect: currentPlayer ? this._buildHandWithSelect(currentPlayer.hand) : [],
      selectedCount: 0
    });
  },

  // 构建带isSelected标记的手牌列表（用于选牌UI）
  _buildHandWithSelect(hand) {
    return hand.map(card => ({ ...card, isSelected: false }));
  },

  // ===== 抽牌阶段 =====

  // 点击"抽取2张牌"
  onDrawCards() {
    const s = this._state;
    const playerIdx = s.drawOrder[s.drawOrderIdx];
    const { state: newState, drawnCards } = drawCards(s, playerIdx);
    this._state = newState;

    // 展示抽到的牌
    this.setData({ drawnCards });
  },

  // 看完抽到的牌，传给下一个人
  onNextDrawPlayer() {
    const s = this._state;
    const nextIdx = s.drawOrderIdx + 1;

    if (nextIdx >= s.numPlayers) {
      // 所有人都抽完了，进入选牌阶段
      this._state = { ...s, drawOrderIdx: nextIdx, phase: 'select' };
    } else {
      this._state = { ...s, drawOrderIdx: nextIdx };
    }
    this._syncToData();
  },

  // ===== 选牌阶段 =====

  // 点击"查看我的牌"（显示手牌）
  onShowHand() {
    const s = this._state;
    const playerIdx = s.selectOrder[s.selectOrderIdx];
    const player = s.players[playerIdx];
    this.setData({
      showHand: true,
      handWithSelect: this._buildHandWithSelect(player.hand),
      selectedCount: 0
    });
  },

  // 点击手牌中的某张牌（选中/取消选中）
  onToggleCard(e) {
    const idx = e.currentTarget.dataset.idx;
    const hand = [...this.data.handWithSelect];
    const card = hand[idx];

    if (card.isSelected) {
      // 取消选中
      hand[idx] = { ...card, isSelected: false };
    } else {
      // 最多只能选2张（第5轮不用选，自动全选）
      const selectedCount = hand.filter(c => c.isSelected).length;
      if (selectedCount >= 2) {
        wx.showToast({ title: '最多选2张牌', icon: 'none' });
        return;
      }
      hand[idx] = { ...card, isSelected: true };
    }

    this.setData({
      handWithSelect: hand,
      selectedCount: hand.filter(c => c.isSelected).length
    });
  },

  // 点击"确认选牌"
  onConfirmSelect() {
    const s = this._state;
    const hand = this.data.handWithSelect;
    const selectedIds = hand.filter(c => c.isSelected).map(c => c.id);

    if (selectedIds.length !== 2) {
      wx.showToast({ title: '请选择2张牌', icon: 'none' });
      return;
    }

    const playerIdx = s.selectOrder[s.selectOrderIdx];
    const newState = confirmSelection(s, playerIdx, selectedIds);
    this._state = newState;
    this._syncToData();
  },

  // ===== 揭示阶段 =====

  // 点击"揭示！同时亮牌"
  onReveal() {
    const { state: newState } = doReveal(this._state);
    this._state = newState;
    this._syncToData();

    // 如果是第4轮，自动标记暗牌为已揭示
    if (this._state.round === 4) {
      this.setData({ revealFaceDown: true });
    }
  },

  // ===== 结算阶段 =====

  // 点击"确认结算"
  onSettleScore() {
    this._state = settleScore(this._state);
    this._syncToData();
  },

  // 点击"下一轮" / "进入结算"
  onNextRound() {
    this._state = nextRound(this._state);
    this._syncToData();
  },

  // ===== 第5轮特殊处理（自动全选剩余手牌）=====
  onRevealRound5() {
    // 第5轮：自动将每人的3张剩余手牌设为confirmedCards
    const s = this._state;
    const players = s.players.map(p => ({
      ...p,
      confirmedCards: [...p.hand]
    }));
    this._state = { ...s, players, phase: 'reveal' };
    // 自动揭示
    const { state: newState } = doReveal(this._state);
    this._state = newState;
    this._syncToData();
  },

  // ===== 游戏结束 =====

  // 再玩一局（返回首页）
  onRestart() {
    wx.navigateBack();
  },

  // 再玩一局（直接重开，保留玩家名字）
  onRestartSamePlayer() {
    const s = this._state;
    const names = s.players.map(p => p.name);
    let newState = initGame(names);
    newState = prepareRound(newState);

    // 保留金豆（累计模式）
    newState.players = newState.players.map((p, i) => ({
      ...p,
      goldBeans: s.players[i] ? s.players[i].goldBeans : 0
    }));

    this._state = newState;
    this._syncToData();
  }
});
