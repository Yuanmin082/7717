// ===================== 牌型定义 =====================
const RANK_ORDER = ['3','4','5','6','7','8','9','10','J','Q','K','A','2','小王','大王'];
const SUITS = ['♠','♥','♦','♣'];

function cardValue(card) {
  return RANK_ORDER.indexOf(card.rank);
}

function createDeck() {
  const deck = [];
  for (const suit of SUITS) {
    for (const rank of RANK_ORDER.slice(0, 13)) {
      deck.push({ rank, suit, id: `${rank}${suit}` });
    }
  }
  deck.push({ rank: '小王', suit: '', id: '小王' });
  deck.push({ rank: '大王', suit: '', id: '大王' });
  return deck;
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function sortCards(cards) {
  return [...cards].sort((a, b) => {
    const va = cardValue(a), vb = cardValue(b);
    if (va !== vb) return va - vb;
    return SUITS.indexOf(a.suit) - SUITS.indexOf(b.suit);
  });
}

// ===================== 牌型识别 =====================
// 返回 { type, rank, cards } 或 null
// type: 'single','pair','triple','bomb','rocket',
//       'triple_single','triple_pair',
//       'straight','pair_straight','plane','plane_single','plane_pair',
//       'four_single','four_pair'

function analyzeHand(cards) {
  if (!cards || cards.length === 0) return null;
  const sorted = sortCards(cards);
  const n = cards.length;
  const rankCount = {};
  for (const c of sorted) {
    rankCount[c.rank] = (rankCount[c.rank] || 0) + 1;
  }
  const counts = Object.values(rankCount).sort((a,b)=>b-a);
  const ranks = sorted.map(c => cardValue(c));

  // 火箭（双王）
  if (n === 2 && sorted[0].rank === '小王' && sorted[1].rank === '大王') {
    return { type: 'rocket', rank: 14, cards: sorted };
  }
  // 炸弹
  if (n === 4 && counts[0] === 4) {
    return { type: 'bomb', rank: cardValue(sorted[0]), cards: sorted };
  }
  // 单张
  if (n === 1) {
    return { type: 'single', rank: cardValue(sorted[0]), cards: sorted };
  }
  // 对子
  if (n === 2 && counts[0] === 2) {
    return { type: 'pair', rank: cardValue(sorted[0]), cards: sorted };
  }
  // 三张
  if (n === 3 && counts[0] === 3) {
    return { type: 'triple', rank: cardValue(sorted[0]), cards: sorted };
  }
  // 三带一
  if (n === 4 && counts[0] === 3) {
    return { type: 'triple_single', rank: rankWithCount(rankCount, 3), cards: sorted };
  }
  // 三带对
  if (n === 5 && counts[0] === 3 && counts[1] === 2) {
    return { type: 'triple_pair', rank: rankWithCount(rankCount, 3), cards: sorted };
  }
  // 四带两单
  if (n === 6 && counts[0] === 4) {
    return { type: 'four_single', rank: rankWithCount(rankCount, 4), cards: sorted };
  }
  // 四带两对
  if (n === 8 && counts[0] === 4) {
    const pairs = Object.entries(rankCount).filter(([,v])=>v===2);
    if (pairs.length === 2) {
      return { type: 'four_pair', rank: rankWithCount(rankCount, 4), cards: sorted };
    }
  }
  // 顺子（5张及以上连续单张，不含2和王）
  if (n >= 5 && counts[0] === 1) {
    const vals = ranks.slice().sort((a,b)=>a-b);
    if (vals[vals.length-1] <= 12 && isConsecutive(vals)) { // 12=A
      return { type: 'straight', rank: vals[vals.length-1], cards: sorted };
    }
  }
  // 连对（3对及以上连续）
  if (n >= 6 && n % 2 === 0 && counts.every(c=>c===2)) {
    const pairRanks = Object.entries(rankCount).map(([r])=>cardValue({rank:r})).sort((a,b)=>a-b);
    if (pairRanks[pairRanks.length-1] <= 12 && isConsecutive(pairRanks) && pairRanks.length >= 3) {
      return { type: 'pair_straight', rank: pairRanks[pairRanks.length-1], cards: sorted };
    }
  }
  // 飞机（两个及以上连续三张）
  const tripleRanks = Object.entries(rankCount).filter(([,v])=>v>=3).map(([r])=>cardValue({rank:r})).sort((a,b)=>a-b);
  if (tripleRanks.length >= 2 && isConsecutive(tripleRanks)) {
    const tc = tripleRanks.length;
    // 纯飞机
    if (n === tc * 3) {
      return { type: 'plane', rank: tripleRanks[tripleRanks.length-1], cards: sorted };
    }
    // 飞机带单
    if (n === tc * 4) {
      return { type: 'plane_single', rank: tripleRanks[tripleRanks.length-1], cards: sorted };
    }
    // 飞机带对
    if (n === tc * 5) {
      const extraCount = Object.values(rankCount).filter(v=>v===2);
      if (extraCount.length === tc) {
        return { type: 'plane_pair', rank: tripleRanks[tripleRanks.length-1], cards: sorted };
      }
    }
  }
  return null;
}

function rankWithCount(rankCount, count) {
  for (const [r, c] of Object.entries(rankCount)) {
    if (c === count) return cardValue({ rank: r });
  }
  return 0;
}

function isConsecutive(vals) {
  for (let i = 1; i < vals.length; i++) {
    if (vals[i] !== vals[i-1] + 1) return false;
  }
  return true;
}

// ===================== 牌型比较 =====================
// 返回 true 表示 newPlay 可以压 lastPlay
function canBeat(newPlay, lastPlay) {
  if (!lastPlay) return true; // 新起手
  // 火箭打所有
  if (newPlay.type === 'rocket') return true;
  // 炸弹打非炸非火
  if (newPlay.type === 'bomb') {
    if (lastPlay.type === 'rocket') return false;
    if (lastPlay.type === 'bomb') return newPlay.rank > lastPlay.rank;
    return true;
  }
  // 其他：必须同类型
  if (lastPlay.type === 'rocket' || lastPlay.type === 'bomb') return false;
  if (newPlay.type !== lastPlay.type) return false;
  if (newPlay.cards.length !== lastPlay.cards.length) {
    // 顺子/连对长度可以不同吗？——不可以，必须同长度
    return false;
  }
  return newPlay.rank > lastPlay.rank;
}

// ===================== 游戏状态 =====================
class Game {
  constructor() {
    this.players = [
      { name: '你', hand: [], isHuman: true, score: 0 },
      { name: '下家', hand: [], isHuman: false, score: 0 },
      { name: '对家', hand: [], isHuman: false, score: 0 },
      { name: '上家', hand: [], isHuman: false, score: 0 },
    ];
    this.currentPlayer = 0;
    this.lastPlay = null;
    this.lastPlayedBy = -1;
    this.passCount = 0;
    this.selectedCards = [];
    this.history = []; // 出牌记录
    this.finishOrder = []; // 出完牌的顺序
    this.gameOver = false;
    this.round = 1;
    this.message = '';
    this.aiThinking = false;
  }

  deal() {
    const deck = shuffle(createDeck());
    for (let i = 0; i < 4; i++) {
      this.players[i].hand = sortCards(deck.slice(i * 13, (i + 1) * 13));
    }
    // 找三方块（3♦）的玩家先手
    this.currentPlayer = 0;
    for (let i = 0; i < 4; i++) {
      if (this.players[i].hand.some(c => c.rank === '3' && c.suit === '♦')) {
        this.currentPlayer = i;
        break;
      }
    }
    this.lastPlay = null;
    this.lastPlayedBy = -1;
    this.passCount = 0;
    this.finishOrder = [];
    this.history = [];
    this.gameOver = false;
    this.selectedCards = [];
    this.message = `${this.players[this.currentPlayer].name} 持有3♦，先手`;
  }

  toggleSelect(card) {
    const idx = this.selectedCards.findIndex(c => c.id === card.id);
    if (idx >= 0) {
      this.selectedCards.splice(idx, 1);
    } else {
      this.selectedCards.push(card);
    }
  }

  playCards(playerIndex, cards) {
    const player = this.players[playerIndex];
    const hand = analyzeHand(cards);
    if (!hand) return { ok: false, msg: '不是合法牌型' };
    if (!canBeat(hand, this.lastPlay)) return { ok: false, msg: '出牌不够大' };

    // 从手牌移除
    for (const c of cards) {
      const idx = player.hand.findIndex(h => h.id === c.id);
      if (idx >= 0) player.hand.splice(idx, 1);
    }
    this.lastPlay = hand;
    this.lastPlayedBy = playerIndex;
    this.passCount = 0;
    this.history.push({ playerIndex, hand });

    // 检查是否出完
    if (player.hand.length === 0) {
      this.finishOrder.push(playerIndex);
      if (this.finishOrder.length >= 3) {
        // 游戏结束
        this.finishOrder.push(...[0,1,2,3].filter(i => !this.finishOrder.includes(i)));
        this.gameOver = true;
        this.settleScore();
        return { ok: true, finished: true };
      }
    }
    return { ok: true };
  }

  pass(playerIndex) {
    if (this.lastPlayedBy === playerIndex) return { ok: false, msg: '新一轮你必须出牌' };
    if (!this.lastPlay) return { ok: false, msg: '新一轮你必须出牌' };
    this.passCount++;
    this.history.push({ playerIndex, pass: true });
    // 检查是否轮回（其他所有人都pass了）
    const activePlayers = [0,1,2,3].filter(i => !this.finishOrder.includes(i));
    if (this.passCount >= activePlayers.length - 1) {
      this.lastPlay = null;
      this.passCount = 0;
      // 找到上次出牌的人，他继续
      this.currentPlayer = this.lastPlayedBy;
      return { ok: true, newRound: true };
    }
    return { ok: true };
  }

  nextPlayer() {
    let next = (this.currentPlayer + 1) % 4;
    while (this.finishOrder.includes(next)) {
      next = (next + 1) % 4;
    }
    this.currentPlayer = next;
  }

  settleScore() {
    // 第1名 +3, 第2名 +1, 第3名 -1, 第4名(老二 逮到了) -3
    const pts = [3, 1, -1, -3];
    for (let i = 0; i < 4; i++) {
      this.players[this.finishOrder[i]].score += pts[i];
    }
  }

  getActivePlayers() {
    return [0,1,2,3].filter(i => !this.finishOrder.includes(i));
  }
}

// ===================== AI 逻辑 =====================
function aiPlay(game, playerIndex) {
  const player = game.players[playerIndex];
  const hand = player.hand;
  const lastPlay = game.lastPlay;
  const mustPlay = !lastPlay || game.lastPlayedBy === playerIndex;

  if (!mustPlay) {
    // 尝试出最小的合法牌
    const play = findBestPlay(hand, lastPlay, false);
    if (play) return { type: 'play', cards: play.cards };
    return { type: 'pass' };
  } else {
    // 必须出牌（新起手）
    const play = findBestPlay(hand, null, true);
    return { type: 'play', cards: play.cards };
  }
}

function findBestPlay(hand, lastPlay, mustPlay) {
  // 生成候选出法并找最小能压住的
  const candidates = generateCandidates(hand);

  if (!lastPlay) {
    // 新起手：出最小单张
    const singles = candidates.filter(c => c.type === 'single');
    if (singles.length > 0) return singles.reduce((a,b) => a.rank < b.rank ? a : b);
    return candidates[0];
  }

  // 找能压住的最小牌型
  const valid = candidates.filter(c => canBeat(c, lastPlay));
  if (valid.length === 0) return null;

  // 优先炸弹排最后
  const nonBomb = valid.filter(c => c.type !== 'bomb' && c.type !== 'rocket');
  const bombs = valid.filter(c => c.type === 'bomb' || c.type === 'rocket');

  const pool = nonBomb.length > 0 ? nonBomb : bombs;
  return pool.reduce((a,b) => a.rank < b.rank ? a : b);
}

function generateCandidates(hand) {
  const candidates = [];
  const n = hand.length;

  // 单张
  for (const c of hand) {
    candidates.push({ type: 'single', rank: cardValue(c), cards: [c] });
  }

  // 对子
  const rankGroups = groupByRank(hand);
  for (const [r, cards] of Object.entries(rankGroups)) {
    if (cards.length >= 2) {
      candidates.push({ type: 'pair', rank: cardValue(cards[0]), cards: cards.slice(0,2) });
    }
    if (cards.length >= 3) {
      candidates.push({ type: 'triple', rank: cardValue(cards[0]), cards: cards.slice(0,3) });
    }
    if (cards.length === 4) {
      candidates.push({ type: 'bomb', rank: cardValue(cards[0]), cards: cards.slice(0,4) });
    }
  }

  // 火箭
  const xw = hand.find(c=>c.rank==='小王');
  const dw = hand.find(c=>c.rank==='大王');
  if (xw && dw) {
    candidates.push({ type: 'rocket', rank: 14, cards: [xw, dw] });
  }

  // 三带一
  for (const [r, cards] of Object.entries(rankGroups)) {
    if (cards.length >= 3) {
      const triple = cards.slice(0,3);
      for (const c of hand) {
        if (c.rank !== r) {
          candidates.push({
            type: 'triple_single',
            rank: cardValue(triple[0]),
            cards: [...triple, c]
          });
          break; // 只生成一个
        }
      }
    }
  }

  // 顺子
  const singleRanks = Object.entries(rankGroups)
    .filter(([r]) => cardValue({rank:r}) <= 12)
    .map(([r, cs]) => ({ v: cardValue({rank:r}), card: cs[0] }))
    .sort((a,b)=>a.v-b.v);

  for (let len = 5; len <= singleRanks.length; len++) {
    for (let start = 0; start <= singleRanks.length - len; start++) {
      const sub = singleRanks.slice(start, start+len);
      if (isConsecutive(sub.map(s=>s.v))) {
        candidates.push({
          type: 'straight',
          rank: sub[sub.length-1].v,
          cards: sub.map(s=>s.card)
        });
      }
    }
  }

  return candidates;
}

function groupByRank(hand) {
  const groups = {};
  for (const c of hand) {
    if (!groups[c.rank]) groups[c.rank] = [];
    groups[c.rank].push(c);
  }
  return groups;
}

// ===================== 导出 =====================
window.Game = Game;
window.analyzeHand = analyzeHand;
window.canBeat = canBeat;
window.sortCards = sortCards;
window.cardValue = cardValue;
window.aiPlay = aiPlay;
