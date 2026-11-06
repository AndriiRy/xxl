// Безопасный парсер формул (без eval). Формулы библиотеки: W-2*t, i==0?-1:1, floor((D-tb-10)/50)*50 ...
(function (K) {
'use strict';
const FN = { min: Math.min, max: Math.max, round: Math.round, floor: Math.floor, ceil: Math.ceil, abs: Math.abs, sqrt: Math.sqrt };
const OPS2 = ['<=', '>=', '==', '!=', '&&', '||'];
const OPS1 = '+-*/%()<>,?:!';

function tokenize(src) {
  const out = []; let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (/\s/.test(c)) { i++; continue; }
    const rest = src.slice(i); let m;
    if ((m = /^(\d+(\.\d+)?|\.\d+)/.exec(rest))) { out.push({ k: 'n', v: parseFloat(m[0]) }); i += m[0].length; continue; }
    if ((m = /^[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё_0-9]*/.exec(rest))) { out.push({ k: 'id', v: m[0] }); i += m[0].length; continue; }
    const two = src.substr(i, 2);
    if (OPS2.includes(two)) { out.push({ k: 'op', v: two }); i += 2; continue; }
    if (OPS1.includes(c)) { out.push({ k: 'op', v: c }); i++; continue; }
    throw new Error('Недопустимый символ «' + c + '» в формуле «' + src + '»');
  }
  return out;
}

function compile(src) {
  const toks = tokenize(src); let p = 0;
  const peek = () => toks[p];
  const isOp = (v) => toks[p] && toks[p].k === 'op' && toks[p].v === v;
  const expect = (v) => { if (!isOp(v)) throw new Error('Ожидалось «' + v + '» в формуле «' + src + '»'); p++; };

  function ternary() {
    const c = orx();
    if (isOp('?')) { p++; const a = ternary(); expect(':'); const b = ternary(); return (s) => (c(s) ? a(s) : b(s)); }
    return c;
  }
  function orx() { let l = andx(); while (isOp('||')) { p++; const r = andx(), a = l; l = (s) => +(!!a(s) || !!r(s)); } return l; }
  function andx() { let l = cmp(); while (isOp('&&')) { p++; const r = cmp(), a = l; l = (s) => +(!!a(s) && !!r(s)); } return l; }
  function cmp() {
    const l = add();
    const t = peek();
    if (t && t.k === 'op' && ['<', '>', '<=', '>=', '==', '!='].includes(t.v)) {
      p++; const r = add(), o = t.v;
      return (s) => { const a = l(s), b = r(s); return +(o === '<' ? a < b : o === '>' ? a > b : o === '<=' ? a <= b : o === '>=' ? a >= b : o === '==' ? Math.abs(a - b) < 1e-9 : Math.abs(a - b) >= 1e-9); };
    }
    return l;
  }
  function add() {
    let l = mul();
    while (isOp('+') || isOp('-')) { const o = toks[p++].v, r = mul(), a = l; l = o === '+' ? (s) => a(s) + r(s) : (s) => a(s) - r(s); }
    return l;
  }
  function mul() {
    let l = un();
    while (isOp('*') || isOp('/') || isOp('%')) {
      const o = toks[p++].v, r = un(), a = l;
      l = o === '*' ? (s) => a(s) * r(s) : o === '/' ? (s) => a(s) / r(s) : (s) => a(s) % r(s);
    }
    return l;
  }
  function un() {
    if (isOp('-')) { p++; const a = un(); return (s) => -a(s); }
    if (isOp('+')) { p++; return un(); }
    if (isOp('!')) { p++; const a = un(); return (s) => +!a(s); }
    return prim();
  }
  function prim() {
    const t = toks[p++];
    if (!t) throw new Error('Неполная формула «' + src + '»');
    if (t.k === 'n') return () => t.v;
    if (t.k === 'id') {
      if (isOp('(')) {
        p++; const args = [];
        if (!isOp(')')) { do { args.push(ternary()); if (isOp(',')) p++; else break; } while (true); }
        expect(')');
        const f = FN[t.v];
        if (!f) throw new Error('Неизвестная функция «' + t.v + '»');
        return (s) => f(...args.map((a) => a(s)));
      }
      const name = t.v;
      return (s) => { if (!(name in s)) throw new Error('Неизвестная переменная «' + name + '» в формуле «' + src + '»'); return s[name]; };
    }
    if (t.k === 'op' && t.v === '(') { const e = ternary(); expect(')'); return e; }
    throw new Error('Неожиданный символ «' + t.v + '» в формуле «' + src + '»');
  }
  const f = ternary();
  if (p < toks.length) throw new Error('Лишний символ «' + toks[p].v + '» в формуле «' + src + '»');
  return f;
}

const cache = new Map();
K.ev = function (src, scope) {
  if (typeof src === 'number') return src;
  if (src === undefined || src === null || String(src).trim() === '') return 0;
  const key = String(src);
  let f = cache.get(key);
  if (!f) { f = compile(key); cache.set(key, f); }
  const v = f(scope);
  if (!Number.isFinite(v)) throw new Error('Формула «' + key + '» дала не число');
  return v;
};
// Шаблон строки: «Направляющие L={rl}» → подстановка значений
K.tpl = function (str, scope) {
  return String(str).replace(/\{([^}]+)\}/g, (m, e) => { try { return String(Math.round(K.ev(e, scope) * 10) / 10); } catch (_) { return m; } });
};
})(window.K = window.K || {});
