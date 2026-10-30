"""
ファイル名: act_loader.py

lerobot-train で学習した ACT の checkpoint(pretrained_model ディレクトリ)を読み込みます。

LeRobot 標準の ACTPolicy.from_pretrained() は設定の読み込みに draccus を使いますが、
draccus は Python 3.14(ROS2 Lyrical の Python)の argparse に対応していないため失敗します。
このモジュールは config.json から ACTConfig を直接組み立てて、draccus を使わずに読み込みます。
(学習は Python 3.12 の .venv-train で lerobot-train を使い、推論は ROS2 と同じ
 Python 3.14 の .venv でこのモジュールを使う)

使用例:
    policy, preprocessor, postprocessor = load_act_policy(path)
    action = postprocessor(policy.select_action(preprocessor(batch)))
"""
import dataclasses
import json
from pathlib import Path
from typing import Any, Optional

from lerobot.configs.types import FeatureType, NormalizationMode, PolicyFeature
from lerobot.policies.act.configuration_act import ACTConfig
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.factory import make_pre_post_processors
from safetensors.torch import load_file


def _to_features(raw: dict[str, Any]) -> dict[str, PolicyFeature]:
    """config.json の features 定義を PolicyFeature の辞書に変換します。"""
    return {
        key: PolicyFeature(type=FeatureType[value['type']], shape=tuple(value['shape']))
        for key, value in raw.items()
    }


def load_act_policy(path: str | Path, device: Optional[str] = None) -> tuple[ACTPolicy, Any, Any]:
    """
    ACT の checkpoint を読み込みます。

    Args:
        path (str | Path): pretrained_model ディレクトリ(config.json と model.safetensors がある場所)
        device (Optional[str]): 推論に使うデバイス('cuda'/'cpu')。None の場合は学習時の設定

    Returns:
        tuple[ACTPolicy, Any, Any]: (評価モードの方策, 前処理パイプライン, 後処理パイプライン)
    """
    path = Path(path)
    raw = json.loads((path / 'config.json').read_text())
    if raw.get('type') != 'act':
        raise ValueError(f"Unsupported policy type: {raw.get('type')!r}")

    init_names = {field.name for field in dataclasses.fields(ACTConfig) if field.init}
    kwargs = {key: value for key, value in raw.items() if key in init_names}
    kwargs['input_features'] = _to_features(raw['input_features'])
    kwargs['output_features'] = _to_features(raw['output_features'])
    kwargs['normalization_mapping'] = {
        key: NormalizationMode[value] for key, value in raw['normalization_mapping'].items()
    }
    # 学習済みの重みで上書きするため、バックボーンの事前学習済み重みはダウンロードしない
    kwargs['pretrained_backbone_weights'] = None
    if device is not None:
        kwargs['device'] = device
    config = ACTConfig(**kwargs)

    policy = ACTPolicy(config)
    policy.load_state_dict(load_file(path / 'model.safetensors'), strict=True)
    policy.to(config.device).eval()

    preprocessor, postprocessor = make_pre_post_processors(
        config,
        pretrained_path=str(path),
        preprocessor_overrides={'device_processor': {'device': config.device}},
    )
    return policy, preprocessor, postprocessor
