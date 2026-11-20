"""Run the allocation study from a dated adjusted-price CSV."""
from pathlib import Path
import argparse
import hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ASSETS = ["US_EQ", "INTL_EQ", "BONDS", "REAL_EST", "GOLD"]
TARGET = np.array([.35, .15, .30, .10, .10])
BENCH = np.array([.60, 0, .40, 0, 0])
RF = .02


def simulate(prices, weights, frequency="Q", bps=5):
    """Trade at the prior close when the next return begins a new calendar period."""
    holdings = weights.astype(float).copy()
    rows = [(1., 0., 0., *np.zeros(len(weights)))]
    dates = prices.index
    periods = dates.to_period(frequency or "Q")
    for i, returns in enumerate(prices.pct_change().iloc[1:].to_numpy(), 1):
        traded = fee = 0.
        if frequency and periods[i] != periods[i - 1]:
            nav = holdings.sum()
            # Solve for post-fee NAV so costs apply to actual buys plus sells.
            post = nav
            for _ in range(12):
                post = nav - np.abs(weights * post - holdings).sum() * bps / 10000
            new = weights * post
            traded = np.abs(new - holdings).sum() / nav
            fee = nav - post
            holdings = new
        pnl = holdings * returns
        holdings += pnl
        rows.append((holdings.sum(), traded, fee, *pnl))
    return pd.DataFrame(rows, index=dates, columns=["NAV", "Gross turnover", "Fee per initial dollar", *prices.columns])


def metrics(nav):
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    r = nav.pct_change().dropna()
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1
    vol = r.std() * np.sqrt(252)
    dd = (nav / nav.cummax() - 1).min()
    sharpe = (r.mean() - ((1 + RF)**(1/252) - 1)) * 252 / vol if vol else np.nan
    return [cagr, vol, sharpe, dd, cagr / abs(dd) if dd else np.nan]


def main(path, out):
    raw = pd.read_csv(path, index_col="Date", parse_dates=True)[ASSETS].apply(pd.to_numeric)
    if raw.index.has_duplicates or raw.index.hasnans:
        raise ValueError("Check duplicate or missing dates.")
    p = raw.sort_index().dropna()
    if len(p) < 3 or not np.isfinite(p).all().all() or (p <= 0).any().any():
        raise ValueError("Expected at least three complete rows of finite positive adjusted prices.")
    out.mkdir(parents=True, exist_ok=True)
    returns = p.pct_change().iloc[1:]
    strategies = {"Policy": (TARGET, "Q"), "Buy and hold": (TARGET, None),
                  "60-40": (BENCH, "Q"), "Equal weight": (np.full(5, .2), "Q")}
    paths = {name: simulate(p, w, freq) for name, (w, freq) in strategies.items()}
    nav = pd.DataFrame({name: frame.NAV for name, frame in paths.items()})
    cols = ["CAGR", "Volatility", "Sharpe", "Max drawdown", "Calmar"]
    summary = pd.DataFrame({n: metrics(nav[n]) for n in nav}, index=cols).T
    summary["Ending wealth per dollar"] = nav.iloc[-1]
    summary["Cumulative gross turnover"] = [f["Gross turnover"].sum() for f in paths.values()]
    summary.to_csv(out/"strategy_metrics.csv")
    nav.to_csv(out/"wealth_paths.csv")
    pd.DataFrame({a: metrics(p[a]) for a in p}, index=cols).T.to_csv(out/"asset_metrics.csv")
    corr = returns.corr()
    corr.to_csv(out/"correlations.csv")
    stresses = []
    attribution = []
    for year in [2008, 2020, 2022]:
        group = nav.loc[nav.index.year == year]
        if group.empty or nav.index[0] >= group.index[0]:
            continue
        window = nav.loc[:group.index[0]].tail(2).iloc[:1]
        window = pd.concat([window, group])
        b = window["60-40"]
        trough = (b / b.cummax() - 1).idxmin()
        peak = b.loc[:trough].idxmax()
        move = window.loc[trough] / window.loc[peak] - 1
        components = {}
        for name in ["Policy", "60-40"]:
            ledger = paths[name]
            interval = ledger.loc[peak:trough].iloc[1:]
            parts = interval[ASSETS].sum() / ledger.loc[peak, "NAV"]
            parts["Trading costs"] = -interval["Fee per initial dollar"].sum() / ledger.loc[peak, "NAV"]
            np.testing.assert_allclose(parts.sum(), move[name], atol=1e-10)
            components[name] = parts
        difference = components["Policy"] - components["60-40"]
        attribution.extend([year, asset, value] for asset, value in difference.items())
        stresses.append([year, peak.date(), trough.date(), move["Policy"], move["60-40"],
                         returns.loc[group.index, "US_EQ"].corr(returns.loc[group.index, "BONDS"])])
    stress = pd.DataFrame(stresses, columns=["Year","Benchmark peak","Benchmark trough","Policy return","Benchmark return","Stock-bond correlation"])
    attrib = pd.DataFrame(attribution, columns=["Year","Exposure","Active contribution"])
    attrib.to_csv(out/"stress_attribution.csv",index=False)
    stress.to_csv(out/"stress_periods.csv", index=False)
    sensitivity = []
    for freq in ["M","Q","Y"]:
        for bps in [0,5,10]:
            sensitivity.append([freq,bps,*metrics(simulate(p,TARGET,freq,bps).NAV)])
    pd.DataFrame(sensitivity, columns=["Frequency","Cost bps",*cols]).to_csv(out/"sensitivity.csv",index=False)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(2,1,figsize=(10,7.5),sharex=True, constrained_layout=True)
    colors = ["#00766e","#9c6808","#203656","#7a6997"]
    for name,color in zip(nav,colors):
        ax[0].plot(nav[name],label=name,color=color,lw=1.6)
        if name in ["Policy","60-40"]:
            ax[1].plot(100*(nav[name]/nav[name].cummax()-1),label=name,color=color,lw=1.3)
    ax[0].set(title="Growth of one dollar",ylabel="Portfolio value (USD)")
    ax[0].legend(ncol=2)
    ax[1].set(title="Distance from the previous peak",ylabel="Drawdown (%)")
    ax[1].legend()
    fig.savefig(out/"performance.png",dpi=155)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.2,5),constrained_layout=True)
    im=ax.imshow(corr,cmap="BrBG",vmin=-1,vmax=1)
    ax.grid(False)
    ax.set_xticks(range(5),["SPY","EFA","AGG","VNQ","GLD"])
    ax.set_yticks(range(5),["SPY","EFA","AGG","VNQ","GLD"])
    ax.set_title("Correlation of daily ETF returns")
    for i in range(5):
        for j in range(5):
            ax.text(j,i,f"{corr.iloc[i,j]:.2f}",ha="center",va="center",color="white" if abs(corr.iloc[i,j])>.65 else "black")
    fig.colorbar(im,ax=ax)
    fig.savefig(out/"correlation.png",dpi=145)
    plt.close(fig)
    a,b,h = [summary.loc[n] for n in ["Policy","60-40","Buy and hold"]]
    gap = 100*(a-b)
    risk = "shallower" if gap["Max drawdown"] > 0 else "deeper"
    growth = "higher" if gap.CAGR > 0 else "lower"
    bullet = (f"Backtested four ETF allocation strategies in Python across {len(returns):,} daily returns. "
              f"The five-ETF policy recorded a {abs(gap['Max drawdown']):.2f}-point {risk} maximum drawdown "
              f"and {abs(gap.CAGR):.2f}-point {growth} annualized growth than a quarterly rebalanced 60/40 benchmark.")
    (out/"resume.txt").write_text(bullet+"\n",encoding="utf8")
    pretty = summary.copy().astype(object)
    for col in cols[:2]+["Max drawdown"]:
        pretty[col] = summary[col].map("{:.2%}".format)
    stress_view=stress.copy()
    for col in ["Policy return","Benchmark return"]:
        stress_view[col]=stress[col].map("{:.2%}".format)
    html=f"""<!doctype html><meta charset="utf-8"><title>Five ETFs versus 60/40</title>
<style>body{{max-width:940px;margin:50px auto;padding:0 20px;color:#203656;font:16px/1.6 system-ui}}h1,h2{{line-height:1.2}}h1{{font: bold 42px Georgia}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:7px;border-bottom:1px solid #ccc;text-align:right}}img{{max-width:100%}}small{{color:#526678}}</style>
<small>PORTFOLIO RESEARCH &nbsp; / &nbsp; BENNETT NGUYEN</small>
<h1>Did five ETFs soften the worst loss?</h1><p>{p.index[0].date()} to {p.index[-1].date()} · {len(returns):,} daily return observations · USD</p>
<p>{bullet}</p><h2>Allocation decision</h2><p>For each initial dollar, the policy allocated 35 cents to SPY, 15 to EFA, 30 to AGG, 10 to VNQ and 10 to GLD. The benchmark invested 60 cents in SPY and 40 in AGG. This comparison measures the combined effect of the allocation changes.</p>
{pretty.to_html(border=0,float_format=lambda v:f'{v:.2f}')}
<img src="performance.png" alt="Historical portfolio growth and drawdown">
<h2>What did rebalancing change?</h2><p>With the same initial holdings, the quarterly policy earned {a.CAGR:.2%} annualized versus {h.CAGR:.2%} for buy and hold. Maximum drawdown was {a['Max drawdown']:.2%} versus {h['Max drawdown']:.2%}. Buy and hold allowed weights to drift. Quarterly trades restored the original exposures and incurred transaction costs.</p>
<h2>Losses over identical dates</h2><p>Each row uses the benchmark's worst peak-to-trough interval within the named calendar year, including the previous year-end as the starting value. The final column measures daily SPY–AGG correlation across that year's available sessions.</p>
{stress_view.to_html(index=False,border=0,float_format=lambda v:f'{v:.2f}')}
<h2>What drove the gap?</h2><p>Each entry is a contribution to the policy return minus the benchmark return over the same peak-to-trough dates. Contributions use actual holdings through each trade. Each column sums to that period’s performance gap, subject to rounding.</p>
{(100*attrib.pivot(index="Exposure",columns="Year",values="Active contribution")).to_html(border=0,float_format=lambda x:f"{x:+.2f} pp")}
<img src="correlation.png" alt="Daily return correlations for five ETFs">
<h2>Interpretation limits</h2><p>Listed real estate also carries equity risk. These proxies and weights were selected retrospectively. One historical path cannot establish which allocation will offer better protection in the next decline. The Sharpe calculation assumes a constant 2% annual risk-free rate. Taxes, initial funding costs and final liquidation are excluded.</p>"""
    (out/"report.html").write_text(html,encoding="utf8")
    (out/"data_audit.txt").write_text(f"Input SHA-256: {hashlib.sha256(path.read_bytes()).hexdigest()}\nRows supplied: {len(raw)}\nComplete dates: {len(p)}\nFirst: {p.index[0].date()}\nLast: {p.index[-1].date()}\nMissing values by column:\n{raw.isna().sum()}\n",encoding="utf8")
    print(bullet)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices", type=Path, default=Path("prices.csv"))
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()
    main(args.prices,args.out)
