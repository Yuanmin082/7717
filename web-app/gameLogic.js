/**
 * 逮老二 - 游戏逻辑（浏览器全局版）
 *
 * phase 状态机：
 *   draw   → 抽牌（第2~4轮轮流抽2张）
 *   select → 选牌（轮流查看手牌并选2张）
 *   reveal → 揭示（同时亮牌）
 *   score  → 结算（显示排名和金豆变化）
 *   end    → 游戏结束
 */

function initGame(playerNames) {
  const numPlayers = playerNames.length;
  const deck = shuffle(createDeck());

  // 桌面4张：前3张明牌，第4张暗牌
  const tableCards = deck.splice(0, 4).map((c, i) => ({ ...c, faceDown: i === 3 }));

  // 每人发5张手牌
  const players = playerNames.map((name, i) => ({
    index: i, name,
    hand: deck.splice(0, 5),
    confirmedCards: [],   // 本轮选定的2张（等待揭示）
    goldBeans: 0
  }));

  return _prepareRound({
    deck, tableCards, players, numPlayers,
    round: 1,
    phase: 'select',
    loserIdx: -1,
    drawOrderIdx: 0,
    selectOrderIdx: 0,
    drawOrder: [],
    selectOrder: [],
    rankings: []
  });
}

/** 准备新一轮（设置抽牌/选牌顺序，清空选牌记录） */
function _prepareRound(state) {
  const { numPlayers, loserIdx, round } = state;

  // 输家先，其余按座位顺序
  const order = Array.from({ length: numPlayers }, (_, i) =>
    loserIdx < 0 ? i : (loserIdx + i) % numPlayers
  );

  const players = state.players.map(p => ({ ...p, confirmedCards: [] }));

  return {
    ...state,
    players,
    drawOrder: order,
    selectOrder: order,
    drawOrderIdx: 0,
    selectOrderIdx: 0,
    rankings: [],
    // 第1轮和第5轮不需要抽牌
    phase: (round === 1 || round === 5) ? 'select' : 'draw'
  };
}

/** 获取本轮参照牌（第1~3轮为明牌，第4轮为暗牌） */
function getTableCardForRound(state) {
  return state.round <= 4 ? state.tableCards[state.round - 1] : null;
}

/** 当前抽牌轮到的玩家下标 */
function currentDrawPlayerIdx(state) {
  return state.drawOrder[state.drawOrderIdx];
}

/** 当前选牌轮到的玩家下标 */
function currentSelectPlayerIdx(state) {
  return state.selectOrder[state.selectOrderIdx];
}

/** 执行抽牌（从牌堆顶取2张给指定玩家） */
function doDrawCards(state, playerIdx) {
  const deck = [...state.deck];
  const drawn = deck.splice(0, 2);
  const players = state.players.map((p, i) =>
    i === playerIdx ? { ...p, hand: [...p.hand, ...drawn] } : p
  );
  return { state: { ...state, deck, players }, drawn };
}

/** 切换到下一个需要抽牌的玩家，若全部抽完则进入选牌阶段 */
function advanceDrawPlayer(state) {
  const nextIdx = state.drawOrderIdx + 1;
  return nextIdx >= state.numPlayers
    ? { ...state, drawOrderIdx: nextIdx, phase: 'select' }
    : { ...state, drawOrderIdx: nextIdx };
}

/** 玩家确认选牌（2张），切换到下一个选牌玩家或进入揭示阶段 */
function confirmSelection(state, playerIdx, selectedIds) {
  const players = state.players.map((p, i) => {
    if (i !== playerIdx) return p;
    return { ...p, confirmedCards: p.hand.filter(c => selectedIds.includes(c.id)) };
  });
  const nextIdx = state.selectOrderIdx + 1;
  return {
    ...state,
    players,
    selectOrderIdx: nextIdx,
    phase: nextIdx >= state.numPlayers ? 'reveal' : 'select'
  };
}

/** 第5轮：自动把每人的3张剩余手牌设为confirmedCards，然后直接进入揭示 */
function prepareRound5Reveal(state) {
  const players = state.players.map(p => ({ ...p, confirmedCards: [...p.hand] }));
  return doReveal({ ...state, players, phase: 'reveal' });
}

/** 揭示：计算每人的3张牌（参照牌+2张，或第5轮的3张手牌），排名 */
function doReveal(state) {
  const { round, tableCards, players } = state;
  const tableCard = tableCards[round - 1];

  const entries = players.map(p => ({
    playerIdx: p.index,
    cards: round === 5 ? [...p.hand] : [tableCard, ...p.confirmedCards]
  }));

  const rankings = rankHands(entries);

  // 第4轮揭开暗牌
  const updatedTableCards = tableCards.map((c, i) =>
    i === 3 ? { ...c, faceDown: false } : c
  );

  return { state: { ...state, rankings, tableCards: updatedTableCards, phase: 'score' }, rankings };
}

/** 结算金豆，从手牌中移除已出的牌，返回含 beansChange 的新state */
function settleScore(state) {
  const { round, rankings } = state;
  const loser = rankings.find(r => r.rank === 2);
  if (!loser) return state;

  const loserIdx = loser.playerIdx;
  const beansPerWinner = round;

  // 第1轮：只有第1名和第3名得豆；其他轮：除第2名外所有人
  const winnerIdxs = rankings
    .filter(r => round === 1 ? (r.rank === 1 || r.rank === 3) : r.rank !== 2)
    .map(r => r.playerIdx);

  const totalLoss = beansPerWinner * winnerIdxs.length;

  const players = state.players.map(p => {
    // 从手牌移除已出的牌（第5轮清空）
    let hand;
    if (round === 5) {
      hand = [];
    } else {
      const usedIds = p.confirmedCards.map(c => c.id);
      hand = p.hand.filter(c => !usedIds.includes(c.id));
    }
    // 更新金豆
    let goldBeans = p.goldBeans;
    if (p.index === loserIdx)         goldBeans -= totalLoss;
    else if (winnerIdxs.includes(p.index)) goldBeans += beansPerWinner;

    return { ...p, hand, confirmedCards: [], goldBeans };
  });

  const rankingsWithBeans = rankings.map(r => ({
    ...r,
    beansChange:
      r.playerIdx === loserIdx      ? -totalLoss :
      winnerIdxs.includes(r.playerIdx) ? +beansPerWinner : 0
  }));

  return { ...state, players, rankings: rankingsWithBeans, loserIdx };
}

/** 进入下一轮 */
function advanceRound(state) {
  const nextRound = state.round + 1;
  if (nextRound > 5) return { ...state, round: nextRound, phase: 'end' };
  return _prepareRound({ ...state, round: nextRound });
}
