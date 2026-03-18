/**
 * 逮老二 Web App - UI 主控制器
 *
 * 所有界面用 innerHTML 渲染，通过事件委托统一处理交互。
 * 游戏逻辑依赖 cards.js 和 gameLogic.js（均为全局函数）。
 */

// ============================================================
// 全局状态
// ============================================================

let G = null;          // 游戏逻辑状态（来自 gameLogic.js）

const UI = {
  screen: 'home',      // 'home' | 'game'
  numPlayers: 3,
  names: ['玩家1', '玩家2', '玩家3', '玩家4'],
  showHand: false,     // 选牌阶段：是否显示手牌
  handCards: [],       // 当前玩家手牌（含 isSelected 标记）
  drawnCards: [],      // 刚抽到的牌
};

// ============================================================
// 应用入口
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
  render();
});

// ============================================================
// 渲染 & 事件绑定
// ============================================================

function render() {
  document.getElementById('app').innerHTML =
    UI.screen === 'home' ? homeHTML() : gameHTML();
  bindEvents();
}

function bindEvents() {
  const app = document.getElementById('app');
  app.onclick = e => {
    const el = e.target.closest('[data-action]');
    if (el) handleAction(el.dataset.action, el.dataset);
  };
  // 输入框：实时保存，不触发重渲染
  app.addEventListener('input', e => {
    if (e.target.dataset.field === 'name') {
      UI.names[+e.target.dataset.idx] = e.target.value || `玩家${+e.target.dataset.idx + 1}`;
    }
  }, { once: true, capture: true });

  // 给 input 再绑定（无 once）
  app.querySelectorAll('[data-field="name"]').forEach(el => {
    el.addEventListener('input', e => {
      UI.names[+e.target.dataset.idx] = e.target.value || `玩家${+e.target.dataset.idx + 1}`;
    });
  });
}

function handleAction(action, data) {
  // 点击前先保存当前所有输入框的值
  document.querySelectorAll('[data-field="name"]').forEach(el => {
    UI.names[+el.dataset.idx] = el.value || `玩家${+el.dataset.idx + 1}`;
  });

  switch (action) {
    case 'set-count':
      UI.numPlayers = +data.count;
      render();
      break;

    case 'start-game':
      startGame();
      break;

    case 'draw-cards': {
      const pidx = currentDrawPlayerIdx(G);
      const { state, drawn } = doDrawCards(G, pidx);
      G = state;
      UI.drawnCards = drawn;
      render();
      break;
    }

    case 'next-draw':
      G = advanceDrawPlayer(G);
      UI.drawnCards = [];
      render();
      break;

    case 'show-hand': {
      const sidx = currentSelectPlayerIdx(G);
      UI.showHand = true;
      UI.handCards = G.players[sidx].hand.map(c => ({ ...c, isSelected: false }));
      render();
      break;
    }

    case 'toggle-card': {
      const idx = +data.idx;
      const cards = [...UI.handCards];
      if (cards[idx].isSelected) {
        cards[idx] = { ...cards[idx], isSelected: false };
      } else {
        const cnt = cards.filter(c => c.isSelected).length;
        if (cnt >= 2) { showTip('最多选2张牌！'); return; }
        cards[idx] = { ...cards[idx], isSelected: true };
      }
      UI.handCards = cards;
      render();
      break;
    }

    case 'confirm-select': {
      const selectedIds = UI.handCards.filter(c => c.isSelected).map(c => c.id);
      if (selectedIds.length !== 2) { showTip('请选择2张牌！'); return; }
      const sidx = currentSelectPlayerIdx(G);
      G = confirmSelection(G, sidx, selectedIds);
      UI.showHand = false;
      UI.handCards = [];
      render();
      break;
    }

    case 'do-reveal': {
      const { state } = doReveal(G);
      G = state;
      render();
      break;
    }

    case 'reveal-r5': {
      const { state } = prepareRound5Reveal(G);
      G = state;
      render();
      break;
    }

    case 'settle':
      G = settleScore(G);
      render();
      break;

    case 'next-round':
      G = advanceRound(G);
      UI.showHand = false;
      UI.handCards = [];
      UI.drawnCards = [];
      render();
      break;

    case 'restart-same': {
      const names = G.players.map(p => p.name);
      const oldBeans = G.players.map(p => p.goldBeans);
      G = initGame(names);
      G.players = G.players.map((p, i) => ({ ...p, goldBeans: (oldBeans[i] || 0) }));
      UI.showHand = false;
      UI.handCards = [];
      UI.drawnCards = [];
      render();
      break;
    }

    case 'go-home':
      G = null;
      UI.screen = 'home';
      UI.showHand = false;
      render();
      break;
  }
}

// ============================================================
// 游戏启动
// ============================================================

function startGame() {
  const names = UI.names.slice(0, UI.numPlayers);
  G = initGame(names);
  UI.screen = 'game';
  UI.showHand = false;
  UI.handCards = [];
  UI.drawnCards = [];
  render();
}

// ============================================================
// 工具函数
// ============================================================

function showTip(msg) {
  const tip = document.createElement('div');
  tip.className = 'float-tip';
  tip.textContent = msg;
  document.body.appendChild(tip);
  setTimeout(() => tip.remove(), 1800);
}

// ============================================================
// 扑克牌 HTML 渲染
// ============================================================

function cardHTML(card, opts = {}) {
  if (!card) return '';

  // 暗牌（未揭示）
  if (card.faceDown) {
    return `<div class="card card-back ${opts.active ? 'card-active' : ''}">
      <span class="card-back-inner">🂠</span>
    </div>`;
  }

  const color = card.isRed ? 'card-red' : 'card-blk';
  const cls = [
    'card', color,
    opts.active   ? 'card-active'   : '',
    opts.selected ? 'card-selected' : '',
    opts.large    ? 'card-lg'       : '',
    opts.mini     ? 'card-mini'     : '',
    opts.clickable? 'card-click'    : '',
  ].filter(Boolean).join(' ');

  const clickAttr = opts.clickable
    ? `data-action="toggle-card" data-idx="${opts.idx}"`
    : '';

  return `<div class="${cls}" ${clickAttr}>
    <span class="cr-top">${card.rank}</span>
    <span class="cs">${card.suit}</span>
    <span class="cr-bot">${card.rank}</span>
  </div>`;
}

// ============================================================
// 首页 HTML
// ============================================================

function homeHTML() {
  const { numPlayers, names } = UI;

  const nameRows = Array.from({ length: numPlayers }, (_, i) => `
    <div class="name-row">
      <label class="name-label">玩家 ${i + 1}</label>
      <input class="name-input" type="text" maxlength="6"
        value="${names[i]}" placeholder="输入名字"
        data-field="name" data-idx="${i}">
    </div>
  `).join('');

  return `
  <div class="home">
    <div class="home-head">
      <div class="home-title">逮老二</div>
      <div class="home-sub">炸金花 · 五轮博弈</div>
    </div>

    <div class="card-section">
      <div class="sec-label">玩家人数</div>
      <div class="count-row">
        <button class="cnt-btn ${numPlayers === 3 ? 'cnt-active' : ''}"
          data-action="set-count" data-count="3">
          <span class="cnt-num">3</span>
          <span class="cnt-sub">人</span>
        </button>
        <button class="cnt-btn ${numPlayers === 4 ? 'cnt-active' : ''}"
          data-action="set-count" data-count="4">
          <span class="cnt-num">4</span>
          <span class="cnt-sub">人</span>
        </button>
      </div>
    </div>

    <div class="card-section">
      <div class="sec-label">玩家名字</div>
      ${nameRows}
    </div>

    <div class="rules-box">
      <div class="rules-title">📋 玩法简介</div>
      <div class="rules-body">
        <p>• 桌面3张明牌 + 1张暗牌，每人发5张手牌</p>
        <p>• 共5轮：从手牌选2张与桌面牌组合，比炸金花大小</p>
        <p>• 排名第2的为输家，给其他人金豆（每轮递增）</p>
        <p>• 第5轮直接展示剩余3张手牌比大小</p>
        <p>• 传手机轮流操作，选牌全程保密，同时揭示</p>
      </div>
    </div>

    <div class="rules-box hand-types-box">
      <div class="rules-title">🃏 牌型大小（炸金花）</div>
      <div class="hand-types">
        <span class="ht">豹子</span>
        <span class="ht-sep">›</span>
        <span class="ht">同花顺</span>
        <span class="ht-sep">›</span>
        <span class="ht">同花</span>
        <span class="ht-sep">›</span>
        <span class="ht">顺子</span>
        <span class="ht-sep">›</span>
        <span class="ht">对子</span>
        <span class="ht-sep">›</span>
        <span class="ht">散牌</span>
      </div>
    </div>

    <button class="start-btn" data-action="start-game">开始游戏 🃏</button>
  </div>`;
}

// ============================================================
// 游戏页面 HTML（顶部始终显示，下方根据 phase 切换）
// ============================================================

function gameHTML() {
  if (!G) return '<div class="loading">加载中...</div>';
  return `
  <div class="game">
    ${headerHTML()}
    ${tableCardsHTML()}
    <div class="phase-area">
      ${phaseHTML()}
    </div>
  </div>`;
}

// ------ 顶部信息栏（轮次 + 金豆）------
function headerHTML() {
  const roundLabels = ['', '第1轮', '第2轮', '第3轮', '第4轮', '第5轮'];
  const phaseLabels = {
    draw: '抽牌', select: '选牌', reveal: '揭示', score: '结算', end: '结束'
  };
  const scoreItems = G.players.map(p => `
    <div class="score-item">
      <span class="s-name">${p.name}</span>
      <span class="s-beans ${p.goldBeans >= 0 ? 'pos' : 'neg'}">
        ${p.goldBeans >= 0 ? '+' : ''}${p.goldBeans}🫘
      </span>
    </div>`).join('');

  return `
  <div class="header">
    <div class="round-badge">
      <span class="r-round">${roundLabels[G.round] || '结束'}</span>
      <span class="r-phase">${phaseLabels[G.phase] || ''}</span>
    </div>
    <div class="score-bar">${scoreItems}</div>
  </div>`;
}

// ------ 桌面4张牌 ------
function tableCardsHTML() {
  const labels = ['明牌1', '明牌2', '明牌3', '暗牌'];
  const cards = G.tableCards.map((c, i) => {
    const isActive = (i === G.round - 1) && G.round <= 4;
    const isRevealPhase = G.phase === 'score' || G.phase === 'end';
    const showFaceDown = (i === 3) && !isRevealPhase;
    return `
    <div class="tc-wrap">
      <span class="tc-label">${labels[i]}</span>
      ${cardHTML(showFaceDown ? c : { ...c, faceDown: false }, { active: isActive })}
    </div>`;
  }).join('');

  return `
  <div class="table-area">
    <span class="area-label">桌面牌</span>
    <div class="table-cards">${cards}</div>
    <span class="table-hint">
      ${G.round <= 4 ? `本轮参照：金框标出的第${G.round}张牌` : '第5轮：展示各自剩余手牌'}
    </span>
  </div>`;
}

// ------ 根据 phase 选择内容 ------
function phaseHTML() {
  switch (G.phase) {
    case 'draw':   return drawPhaseHTML();
    case 'select': return selectPhaseHTML();
    case 'reveal': return revealPhaseHTML();
    case 'score':  return scorePhaseHTML();
    case 'end':    return endPhaseHTML();
    default: return '';
  }
}

// ============================================================
// 抽牌阶段
// ============================================================

function drawPhaseHTML() {
  const pidx = currentDrawPlayerIdx(G);
  const player = G.players[pidx];
  const drawnCount = UI.drawnCards.length;
  const allDrawn = G.drawOrderIdx >= G.numPlayers;

  if (allDrawn) {
    return `<div class="phase-box">
      <div class="ph-title">📦 所有人已抽牌</div>
      <div class="ph-desc">准备开始选牌！</div>
    </div>`;
  }

  return `
  <div class="phase-box">
    <div class="ph-title">📦 抽牌阶段</div>
    <div class="player-turn-banner">
      <span class="turn-arrow">▶</span>
      <span class="turn-name">${player.name}</span>
      <span class="turn-desc">请抽取2张牌</span>
    </div>
    <div class="ph-hint">其他玩家请背对屏幕</div>

    ${drawnCount === 0 ? `
      <button class="btn btn-primary" data-action="draw-cards">
        🎴 抽取2张牌
      </button>
    ` : `
      <div class="drawn-result">
        <div class="drawn-label">抽到的牌：</div>
        <div class="drawn-cards">
          ${UI.drawnCards.map(c => cardHTML(c, { large: true })).join('')}
        </div>
        <div class="ph-hint">看好你的牌，然后把手机传给下一位</div>
        <button class="btn btn-secondary" data-action="next-draw">
          传给下家 →
        </button>
      </div>
    `}
  </div>`;
}

// ============================================================
// 选牌阶段
// ============================================================

function selectPhaseHTML() {
  // 第5轮：不需要选，直接展示
  if (G.round === 5) {
    return `
    <div class="phase-box">
      <div class="ph-title">🃏 第5轮 · 展示手牌</div>
      <div class="ph-desc">每人展示剩余的3张手牌，排名第2的输家给所有人各5颗金豆</div>
      <button class="btn btn-reveal" data-action="reveal-r5">
        同时展示所有手牌 👁
      </button>
    </div>`;
  }

  const sidx = currentSelectPlayerIdx(G);
  const player = G.players[sidx];
  const doneCount = G.selectOrderIdx;
  const tableCard = getTableCardForRound(G);

  if (!UI.showHand) {
    // 未看牌状态
    return `
    <div class="phase-box">
      <div class="ph-title">🃏 选牌阶段</div>
      <div class="progress-bar">
        ${G.selectOrder.map((pi, i) => `
          <span class="pb-item ${i < doneCount ? 'pb-done' : i === doneCount ? 'pb-cur' : ''}">
            ${G.players[pi].name}${i < doneCount ? '✓' : ''}
          </span>
        `).join('<span class="pb-sep">›</span>')}
      </div>

      <div class="player-turn-banner">
        <span class="turn-arrow">▶</span>
        <span class="turn-name">${player.name}</span>
        <span class="turn-desc">请查看并选牌</span>
      </div>
      <div class="ph-hint">其他玩家请背对屏幕</div>

      <div class="ref-hint">
        本轮参照牌：
        ${cardHTML(tableCard, {})}
        请从手牌中选2张，与参照牌组成炸金花最强或最弱的组合
      </div>

      <button class="btn btn-primary" data-action="show-hand">
        👀 查看我的手牌
      </button>
    </div>`;
  }

  // 显示手牌，允许选择
  const selectedCnt = UI.handCards.filter(c => c.isSelected).length;
  const handHtml = UI.handCards.map((c, i) =>
    cardHTML(c, { clickable: true, selected: c.isSelected, idx: i })
  ).join('');

  return `
  <div class="phase-box">
    <div class="ph-title">🃏 ${player.name} 的手牌</div>

    <div class="ref-line">
      <span class="ref-txt">参照牌：</span>
      ${cardHTML(tableCard, {})}
    </div>

    <div class="ph-hint">点击牌面选中/取消，请选2张</div>

    <div class="hand-area">${handHtml}</div>

    <div class="selected-count">已选 <strong>${selectedCnt}</strong> / 2 张</div>

    <button class="btn ${selectedCnt === 2 ? 'btn-confirm' : 'btn-disabled'}"
      ${selectedCnt !== 2 ? 'disabled' : ''}
      data-action="confirm-select">
      ✅ 确认选牌，传给下家
    </button>
  </div>`;
}

// ============================================================
// 揭示阶段
// ============================================================

function revealPhaseHTML() {
  const tableCard = G.round <= 4 ? G.tableCards[G.round - 1] : null;

  const playerRows = G.players.map(p => {
    const showCards = G.round === 5
      ? p.hand   // 第5轮：3张手牌
      : p.confirmedCards; // 其他轮：选的2张

    return `
    <div class="reveal-row">
      <span class="reveal-name">${p.name}</span>
      <div class="reveal-cards">
        ${G.round < 5 && tableCard ? cardHTML({ ...tableCard, faceDown: false }, { active: true }) : ''}
        ${showCards.map(c => cardHTML(c)).join('')}
      </div>
    </div>`;
  }).join('');

  return `
  <div class="phase-box">
    <div class="ph-title">👀 所有人已选好！</div>
    <div class="ph-desc">
      ${G.round === 4 ? '第4轮：揭示暗牌！' : '准备同时揭示！'}
    </div>

    <div class="reveal-list">${playerRows}</div>

    <button class="btn btn-reveal" data-action="do-reveal">
      揭示排名！🏆
    </button>
  </div>`;
}

// ============================================================
// 结算阶段
// ============================================================

function scorePhaseHTML() {
  const rankIcons = ['', '🥇', '💀', '🥉', '4️⃣'];
  const tableCard = G.round <= 4 ? { ...G.tableCards[G.round - 1], faceDown: false } : null;

  const rows = G.rankings.map(r => {
    const player = G.players[r.playerIdx];
    const isLoser = r.rank === 2;

    // 展示的3张牌
    const displayCards = G.round === 5
      ? r.cards
      : r.hand.cards; // 已排序的3张

    const cardsHtml = displayCards.map(c => cardHTML(c, { mini: true })).join('');
    const bChange = r.beansChange;

    return `
    <div class="rank-row ${isLoser ? 'loser-row' : ''}">
      <span class="rank-icon">${rankIcons[r.rank] || r.rank}</span>
      <span class="rank-name">${player.name}</span>
      <div class="rank-cards">${cardsHtml}</div>
      <span class="rank-type">${r.hand.typeName}</span>
      <span class="rank-beans ${bChange > 0 ? 'pos' : bChange < 0 ? 'neg' : ''}">
        ${bChange > 0 ? '+' : ''}${bChange}🫘
      </span>
    </div>`;
  }).join('');

  const loserRule = G.round === 1
    ? '第2名输家给第1名和第3名各1颗金豆'
    : `第2名输家给每位赢家各${G.round}颗金豆`;

  const isLastRound = G.round === 5;

  return `
  <div class="phase-box">
    <div class="ph-title">🏆 本轮排名</div>

    <div class="ranking-list">${rows}</div>

    <div class="rule-tip">💡 ${loserRule}</div>

    <button class="btn btn-primary" data-action="${isLastRound ? 'settle' : 'settle'}">
      ${isLastRound ? '确认结算，查看最终结果' : `确认结算，进入第${G.round + 1}轮`}
    </button>
  </div>`;
}

// ============================================================
// 游戏结束
// ============================================================

function endPhaseHTML() {
  // 按金豆从高到低排序
  const sorted = [...G.players].sort((a, b) => b.goldBeans - a.goldBeans);
  const winner = sorted[0];

  const rows = sorted.map((p, i) => `
    <div class="final-row">
      <span class="final-rank">${['🥇','🥈','🥉','4️⃣'][i]}</span>
      <span class="final-name">${p.name}</span>
      <span class="final-beans ${p.goldBeans >= 0 ? 'pos' : 'neg'}">
        ${p.goldBeans >= 0 ? '+' : ''}${p.goldBeans} 🫘
      </span>
    </div>
  `).join('');

  return `
  <div class="phase-box end-box">
    <div class="ph-title">🎉 游戏结束！</div>

    <div class="winner-banner">
      <div class="winner-label">本局冠军</div>
      <div class="winner-name">🏆 ${winner.name}</div>
      <div class="winner-beans">${winner.goldBeans >= 0 ? '+' : ''}${winner.goldBeans} 🫘</div>
    </div>

    <div class="final-list">${rows}</div>

    <button class="btn btn-primary" data-action="restart-same">
      再来一局（金豆累计）
    </button>
    <button class="btn btn-secondary" data-action="go-home">
      返回首页
    </button>
  </div>`;
}
