/**
 * 逮老二 - 游戏逻辑
 *
 * === 游戏流程 ===
 * 1. 发牌：桌面发3张明牌+1张暗牌，每位玩家发5张手牌
 * 2. 第1轮：参照第1张明牌，每人选2张手牌同时展示，排名第2的输
 *           输家给第1名和第3名各1颗金豆
 * 3. 第2轮：上轮输家先抽2张，其他人各抽2张，参照第2张明牌出牌
 *           输家给每个其他玩家2颗金豆
 * 4. 第3轮：同上，输家给每人3颗金豆
 * 5. 第4轮：参照暗牌（揭示），先各抽2张，出2张，揭示暗牌比较
 *           输家给每人4颗金豆
 * 6. 第5轮：不抽牌，展示剩余3张手牌，输家给每人5颗金豆
 * 游戏结束，可重新开始
 */

const { createDeck, shuffle, rankHands } = require('./cards');

/**
 * 初始化游戏状态
 * @param {string[]} playerNames - 玩家名字数组（3或4个）
 * @returns {Object} 初始游戏状态
 */
function initGame(playerNames) {
  const numPlayers = playerNames.length;
  const deck = shuffle(createDeck());

  // 桌面发4张牌（3明1暗）
  const tableCards = [];
  for (let i = 0; i < 4; i++) {
    const card = deck.shift();
    card.faceDown = (i === 3); // 第4张是暗牌
    tableCards.push(card);
  }

  // 每人发5张手牌
  const players = playerNames.map((name, i) => ({
    index: i,
    name,
    hand: deck.splice(0, 5),       // 手牌（最多5张）
    selected: [],                   // 本轮选中的2张
    confirmedCards: [],             // 已确认的牌（等待揭示）
    goldBeans: 0                    // 金豆数量
  }));

  return {
    deck,          // 剩余牌堆（待抽）
    tableCards,    // 桌面4张牌
    players,
    numPlayers,
    round: 1,      // 当前轮次（1~5）
    // 阶段：draw（抽牌）| select（选牌）| reveal（揭示）| score（结算）| end（结束）
    phase: 'select',
    loserIdx: -1,  // 上轮输家的下标（-1表示第一轮）
    drawOrderIdx: 0,   // 当前抽牌顺序（draw阶段用）
    selectOrderIdx: 0, // 当前选牌顺序（select阶段用）
    drawOrder: [],     // 本轮抽牌顺序（输家排第一）
    selectOrder: [],   // 本轮选牌顺序
    rankings: [],      // 本轮排名结果
    roundHistory: []   // 历史记录
  };
}

/**
 * 获取某一轮对应的桌面参照牌
 * @param {Object} state
 * @returns {Object} 参照牌（第1~3轮为明牌，第4轮为暗牌）
 */
function getTableCardForRound(state) {
  return state.tableCards[state.round - 1];
}

/**
 * 准备新的一轮（设置抽牌/选牌顺序）
 * @param {Object} state
 * @returns {Object} 更新后的state
 */
function prepareRound(state) {
  const { numPlayers, loserIdx, round } = state;

  // 确定本轮顺序（输家排第一，其他人按座位顺序）
  let order = [];
  if (loserIdx < 0) {
    // 第一轮：按座位顺序0,1,2...
    order = Array.from({ length: numPlayers }, (_, i) => i);
  } else {
    // 之后轮次：输家先
    for (let i = 0; i < numPlayers; i++) {
      order.push((loserIdx + i) % numPlayers);
    }
  }

  // 清空每人的选牌记录
  const players = state.players.map(p => ({
    ...p,
    selected: [],
    confirmedCards: []
  }));

  const newState = {
    ...state,
    players,
    drawOrder: order,
    selectOrder: order,
    drawOrderIdx: 0,
    selectOrderIdx: 0,
    rankings: []
  };

  // 第1轮和第5轮不需要抽牌
  if (round === 1 || round === 5) {
    newState.phase = 'select';
  } else {
    newState.phase = 'draw';
  }

  return newState;
}

/**
 * 玩家抽牌（2张）
 * @param {Object} state
 * @param {number} playerIdx - 要抽牌的玩家下标
 * @returns {{ state, drawnCards }} 更新后的state和抽到的牌
 */
function drawCards(state, playerIdx) {
  const drawnCards = state.deck.splice(0, 2);
  const players = state.players.map((p, i) => {
    if (i === playerIdx) {
      return { ...p, hand: [...p.hand, ...drawnCards] };
    }
    return p;
  });
  return {
    state: { ...state, players, deck: [...state.deck] },
    drawnCards
  };
}

/**
 * 玩家确认选牌
 * @param {Object} state
 * @param {number} playerIdx - 玩家下标
 * @param {string[]} selectedIds - 选中的牌的id列表
 * @returns {Object} 更新后的state
 */
function confirmSelection(state, playerIdx, selectedIds) {
  const players = state.players.map((p, i) => {
    if (i !== playerIdx) return p;
    const confirmedCards = p.hand.filter(c => selectedIds.includes(c.id));
    return { ...p, confirmedCards, selected: [] };
  });

  const nextIdx = state.selectOrderIdx + 1;
  const allDone = nextIdx >= state.numPlayers;

  return {
    ...state,
    players,
    selectOrderIdx: nextIdx,
    phase: allDone ? 'reveal' : 'select'
  };
}

/**
 * 揭示并排名
 * @param {Object} state
 * @returns {{ state, rankings }} 排名结果
 */
function doReveal(state) {
  const { round, tableCards } = state;
  const tableCard = tableCards[round - 1]; // 参照牌（第4轮为暗牌）

  // 组合每个玩家的牌（参照牌+选的2张，或第5轮的3张手牌）
  const entries = state.players.map(p => {
    let cards;
    if (round === 5) {
      // 第5轮：直接用全部剩余手牌（3张）
      cards = [...p.hand];
    } else {
      // 其他轮：参照牌 + 玩家选的2张
      cards = [tableCard, ...p.confirmedCards];
    }
    return { playerIdx: p.index, cards };
  });

  const rankings = rankHands(entries);

  // 把暗牌标记为已揭示
  const updatedTableCards = tableCards.map((c, i) => {
    if (i === 3) return { ...c, faceDown: false };
    return c;
  });

  return {
    state: { ...state, rankings, tableCards: updatedTableCards, phase: 'score' },
    rankings
  };
}

/**
 * 结算金豆
 * @param {Object} state
 * @returns {Object} 更新后的state（含金豆变化）
 */
function settleScore(state) {
  const { round, rankings, numPlayers } = state;
  const beansPerWinner = round; // 第N轮，赢家各得N颗

  // 找到第2名（输家）
  const loser = rankings.find(r => r.rank === 2);
  if (!loser) return state;

  const loserIdx = loser.playerIdx;

  // 确定赢家（第1轮：1名和3名；其他轮：除2名外所有人）
  let winnerIdxs;
  if (round === 1) {
    // 第1轮特殊规则：只有第1名和第3名各得1豆
    winnerIdxs = rankings
      .filter(r => r.rank === 1 || r.rank === 3)
      .map(r => r.playerIdx);
  } else {
    // 其他轮：除第2名外所有人
    winnerIdxs = rankings
      .filter(r => r.rank !== 2)
      .map(r => r.playerIdx);
  }

  const totalLoss = beansPerWinner * winnerIdxs.length;

  // 更新金豆
  const players = state.players.map(p => {
    if (p.index === loserIdx) {
      return { ...p, goldBeans: p.goldBeans - totalLoss };
    }
    if (winnerIdxs.includes(p.index)) {
      return { ...p, goldBeans: p.goldBeans + beansPerWinner };
    }
    return p;
  });

  // 第5轮后从手牌移除（其实手牌已展示，清空即可）
  // 第1~4轮：从手牌移除已出的2张
  const updatedPlayers = players.map(p => {
    if (round < 5) {
      const confirmedIds = p.confirmedCards.map(c => c.id);
      return { ...p, hand: p.hand.filter(c => !confirmedIds.includes(c.id)), confirmedCards: [] };
    }
    return { ...p, hand: [], confirmedCards: [] };
  });

  return {
    ...state,
    players: updatedPlayers,
    loserIdx,
    rankings: rankings.map(r => ({
      ...r,
      beansChange: r.playerIdx === loserIdx
        ? -totalLoss
        : (winnerIdxs.includes(r.playerIdx) ? +beansPerWinner : 0)
    }))
  };
}

/**
 * 进入下一轮
 * @param {Object} state
 * @returns {Object} 更新后的state
 */
function nextRound(state) {
  const nextRound = state.round + 1;
  if (nextRound > 5) {
    return { ...state, phase: 'end', round: nextRound };
  }
  const newState = { ...state, round: nextRound };
  return prepareRound(newState);
}

module.exports = {
  initGame,
  prepareRound,
  getTableCardForRound,
  drawCards,
  confirmSelection,
  doReveal,
  settleScore,
  nextRound
};
