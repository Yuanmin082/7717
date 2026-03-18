/**
 * 扑克牌工具库
 * 包含：创建牌组、洗牌、炸金花牌型判断、比大小
 */

// 花色（黑桃、红心、方块、梅花）
const SUITS = ['♠', '♥', '♦', '♣'];

// 点数（从小到大）
const RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];

// 点数对应数字大小（用于比较）
const RANK_VAL = {
  '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
  '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
};

/**
 * 创建一副完整的52张扑克牌
 */
function createDeck() {
  const deck = [];
  SUITS.forEach(suit => {
    RANKS.forEach(rank => {
      deck.push({
        rank,
        suit,
        value: RANK_VAL[rank],
        id: `${rank}${suit}`,
        isRed: suit === '♥' || suit === '♦',
        display: rank + suit   // 显示文字，如 "A♠"
      });
    });
  });
  return deck;
}

/**
 * 洗牌（随机打乱顺序）
 */
function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/**
 * 判断三张牌是否构成顺子
 * A-2-3 是最小的顺子，Q-K-A 是最大的顺子
 */
function isStraight(vals) {
  const s = [...vals].sort((a, b) => a - b);
  // 普通顺子：三张连续
  if (s[2] - s[1] === 1 && s[1] - s[0] === 1) return true;
  // 特殊顺子：A-2-3（A值为14，当1用）
  if (s[0] === 2 && s[1] === 3 && s[2] === 14) return true;
  return false;
}

/**
 * 获取顺子的比较值（用于比大小）
 * A-2-3 最小，Q-K-A 最大
 */
function straightHighVal(vals) {
  const s = [...vals].sort((a, b) => a - b);
  if (s[0] === 2 && s[1] === 3 && s[2] === 14) return 3; // A-2-3 按3算（最低顺子）
  return s[2]; // 其他顺子按最大牌算
}

/**
 * 评估三张牌的牌型（炸金花规则）
 * 牌型从大到小：豹子 > 同花顺 > 同花 > 顺子 > 对子 > 散牌
 *
 * @param {Array} cards - 三张牌的数组
 * @returns {Object} 包含牌型信息的对象
 */
function evaluateHand(cards) {
  if (!cards || cards.length !== 3) {
    return { type: 0, typeName: '无效', cards: [] };
  }

  // 按点数从大到小排序
  const sorted = [...cards].sort((a, b) => b.value - a.value);
  const vals = sorted.map(c => c.value);
  const suits = sorted.map(c => c.suit);

  // 判断各种牌型
  const isFlush = suits[0] === suits[1] && suits[1] === suits[2]; // 同花
  const hasStraight = isStraight(vals);                           // 顺子
  const isLeopard = vals[0] === vals[1] && vals[1] === vals[2];   // 豹子（三条）

  // 判断对子
  let pairVal = -1, kickerVal = -1;
  if (vals[0] === vals[1]) { pairVal = vals[0]; kickerVal = vals[2]; }
  else if (vals[1] === vals[2]) { pairVal = vals[1]; kickerVal = vals[0]; }
  else if (vals[0] === vals[2]) { pairVal = vals[0]; kickerVal = vals[1]; }
  const hasPair = pairVal > -1;

  // 确定牌型编号（数字越大牌型越大）
  let type, typeName;
  if (isLeopard)            { type = 6; typeName = '豹子'; }
  else if (isFlush && hasStraight) { type = 5; typeName = '同花顺'; }
  else if (isFlush)         { type = 4; typeName = '同花'; }
  else if (hasStraight)     { type = 3; typeName = '顺子'; }
  else if (hasPair)         { type = 2; typeName = '对子'; }
  else                      { type = 1; typeName = '散牌'; }

  return {
    type,
    typeName,
    cards: sorted,
    vals,       // 各牌点数（排序后）
    isFlush,
    hasStraight,
    isLeopard,
    hasPair,
    pairVal,    // 对子的点数
    kickerVal,  // 对子旁的单张点数
    straightHigh: hasStraight ? straightHighVal(vals) : 0
  };
}

/**
 * 比较两手牌（炸金花规则）
 * @returns 1 表示 h1 赢，-1 表示 h2 赢，0 表示平局
 */
function compareHands(h1, h2) {
  // 先比牌型
  if (h1.type !== h2.type) return h1.type > h2.type ? 1 : -1;

  // 同牌型，比具体大小
  switch (h1.type) {
    case 6: // 豹子：比点数
      return h1.vals[0] > h2.vals[0] ? 1 : h1.vals[0] < h2.vals[0] ? -1 : 0;

    case 5: // 同花顺：比最高牌
    case 3: // 顺子
      return h1.straightHigh > h2.straightHigh ? 1 : h1.straightHigh < h2.straightHigh ? -1 : 0;

    case 4: // 同花：依次比第1、2、3张
    case 1: // 散牌
      for (let i = 0; i < 3; i++) {
        if (h1.vals[i] !== h2.vals[i]) return h1.vals[i] > h2.vals[i] ? 1 : -1;
      }
      return 0;

    case 2: // 对子：先比对子点数，再比单张
      if (h1.pairVal !== h2.pairVal) return h1.pairVal > h2.pairVal ? 1 : -1;
      return h1.kickerVal > h2.kickerVal ? 1 : h1.kickerVal < h2.kickerVal ? -1 : 0;

    default:
      return 0;
  }
}

/**
 * 对多名玩家的牌进行排名
 * @param {Array} entries - [{playerIdx, cards}]
 * @returns {Array} 排名结果，rank=1最大，rank=N最小
 */
function rankHands(entries) {
  // 每个 entry 加上牌型评估
  const withHands = entries.map(e => ({
    ...e,
    hand: evaluateHand(e.cards)
  }));

  // 从大到小排序
  withHands.sort((a, b) => compareHands(b.hand, a.hand));

  // 标注名次
  return withHands.map((item, i) => ({
    ...item,
    rank: i + 1
  }));
}

module.exports = { createDeck, shuffle, evaluateHand, rankHands, RANK_VAL };
