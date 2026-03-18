/**
 * 扑克牌工具库（浏览器全局版）
 * 炸金花牌型：豹子 > 同花顺 > 同花 > 顺子 > 对子 > 散牌
 */

const SUITS = ['♠', '♥', '♦', '♣'];
const RANKS = ['2','3','4','5','6','7','8','9','10','J','Q','K','A'];
const RANK_VAL = {
  '2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,
  '9':9,'10':10,'J':11,'Q':12,'K':13,'A':14
};

function createDeck() {
  const deck = [];
  SUITS.forEach(suit => {
    RANKS.forEach(rank => {
      deck.push({
        rank, suit,
        value: RANK_VAL[rank],
        id: `${rank}${suit}`,
        isRed: suit === '♥' || suit === '♦'
      });
    });
  });
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

function _isStraight(vals) {
  const s = [...vals].sort((a, b) => a - b);
  if (s[2] - s[1] === 1 && s[1] - s[0] === 1) return true;
  // A-2-3 特殊顺子
  if (s[0] === 2 && s[1] === 3 && s[2] === 14) return true;
  return false;
}

function _straightHigh(vals) {
  const s = [...vals].sort((a, b) => a - b);
  if (s[0] === 2 && s[1] === 3 && s[2] === 14) return 3; // 最小顺子
  return s[2];
}

function evaluateHand(cards) {
  if (!cards || cards.length !== 3) return { type: 0, typeName: '无效', cards: [] };
  const sorted = [...cards].sort((a, b) => b.value - a.value);
  const vals = sorted.map(c => c.value);
  const suits = sorted.map(c => c.suit);

  const isFlush     = suits[0] === suits[1] && suits[1] === suits[2];
  const hasStraight = _isStraight(vals);
  const isLeopard   = vals[0] === vals[1] && vals[1] === vals[2];

  let pairVal = -1, kickerVal = -1;
  if      (vals[0] === vals[1]) { pairVal = vals[0]; kickerVal = vals[2]; }
  else if (vals[1] === vals[2]) { pairVal = vals[1]; kickerVal = vals[0]; }
  else if (vals[0] === vals[2]) { pairVal = vals[0]; kickerVal = vals[1]; }
  const hasPair = pairVal > -1;

  let type, typeName;
  if      (isLeopard)            { type = 6; typeName = '豹子'; }
  else if (isFlush && hasStraight){ type = 5; typeName = '同花顺'; }
  else if (isFlush)              { type = 4; typeName = '同花'; }
  else if (hasStraight)          { type = 3; typeName = '顺子'; }
  else if (hasPair)              { type = 2; typeName = '对子'; }
  else                           { type = 1; typeName = '散牌'; }

  return {
    type, typeName, cards: sorted, vals,
    isFlush, hasStraight, isLeopard, hasPair, pairVal, kickerVal,
    straightHigh: hasStraight ? _straightHigh(vals) : 0
  };
}

function compareHands(h1, h2) {
  if (h1.type !== h2.type) return h1.type > h2.type ? 1 : -1;
  switch (h1.type) {
    case 6: return h1.vals[0] > h2.vals[0] ? 1 : h1.vals[0] < h2.vals[0] ? -1 : 0;
    case 5: case 3:
      return h1.straightHigh > h2.straightHigh ? 1 : h1.straightHigh < h2.straightHigh ? -1 : 0;
    case 4: case 1:
      for (let i = 0; i < 3; i++) {
        if (h1.vals[i] !== h2.vals[i]) return h1.vals[i] > h2.vals[i] ? 1 : -1;
      }
      return 0;
    case 2:
      if (h1.pairVal !== h2.pairVal) return h1.pairVal > h2.pairVal ? 1 : -1;
      return h1.kickerVal > h2.kickerVal ? 1 : h1.kickerVal < h2.kickerVal ? -1 : 0;
    default: return 0;
  }
}

function rankHands(entries) {
  return [...entries]
    .map(e => ({ ...e, hand: evaluateHand(e.cards) }))
    .sort((a, b) => compareHands(b.hand, a.hand))
    .map((item, i) => ({ ...item, rank: i + 1 }));
}
