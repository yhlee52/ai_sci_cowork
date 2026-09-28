"""범용 PyTorch 학습 루프. AMP, 시간 예산, 체크포인트 이어하기를 지원한다 (10분 단위 명령으로 나눠 돌릴 때 사용).

    from labkit.train import fit
    best = fit(model, opt, loss_fn, train_loader, run, epochs=20, eval_fn=lambda m: {"val_acc": ...})
"""
from __future__ import annotations

from typing import Callable

import torch

from .repro import get_device
from .run import Run


def fit(model: torch.nn.Module, optimizer: torch.optim.Optimizer, loss_fn: Callable, train_loader, run: Run,
        epochs: int, eval_fn: Callable[[torch.nn.Module], dict] | None = None, monitor: str | None = None,
        mode: str = "max", amp: bool = True, grad_clip: float | None = None, scheduler=None,
        ckpt_every: int = 1, log_every: int = 50) -> dict:
    """학습하고, `monitor` 기준 최고 평가 지표(없으면 마지막 지표)를 돌려준다. runs/<id>/ckpt.pt가 있으면 이어서 학습한다."""
    device = get_device()
    model.to(device)
    use_amp = amp and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    ckpt = run.dir / "ckpt.pt"
    start_epoch, step, best = 0, 0, None
    if ckpt.exists():
        state = torch.load(ckpt, map_location=device)
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        if scheduler and state.get("scheduler"):
            scheduler.load_state_dict(state["scheduler"])
        start_epoch, step, best = state["epoch"] + 1, state["step"], state.get("best")
        run.logger.info(f"{start_epoch} 에폭부터 이어서 학습")

    last: dict = {}
    for epoch in range(start_epoch, epochs):
        model.train()
        for xb, yb in train_loader:
            xb, yb = xb.to(device, non_blocking=True), yb.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=use_amp):
                loss = loss_fn(model(xb), yb)
            scaler.scale(loss).backward()
            if grad_clip:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            scaler.step(optimizer)
            scaler.update()
            if step % log_every == 0:
                run.log(step, epoch=epoch, loss=loss.item())
            step += 1
        if scheduler:
            scheduler.step()
        if eval_fn:
            model.eval()
            with torch.no_grad():
                last = eval_fn(model)
            run.log(step, epoch=epoch, **last)
            if monitor and monitor in last:
                v = last[monitor]
                if best is None or (v > best[monitor] if mode == "max" else v < best[monitor]):
                    best = dict(last)
        if (epoch + 1) % ckpt_every == 0 or epoch == epochs - 1:
            torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                        "scheduler": scheduler.state_dict() if scheduler else None,
                        "epoch": epoch, "step": step, "best": best}, ckpt)
        if run.over_budget():
            run.logger.info(f"{epoch} 에폭에서 시간 예산 도달")
            break
    return best or last
