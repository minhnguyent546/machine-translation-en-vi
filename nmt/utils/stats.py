import numpy as np

from torch import Tensor
from torch.utils.tensorboard import SummaryWriter
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
)

class Stats:
    def __init__(
        self,
        num_batchs: int = 0,
        loss: float = 0.0,
        pred: list[np.ndarray] = [],
        labels: list[np.ndarray] = [],
        f_score_beta: float = 0.5,
        average='weighted',
        pad_token_id: int | None = None,
        ignore_padding: bool = False,
    ) -> None:
        self.num_batchs = num_batchs
        self.loss = loss
        self.pred = pred
        self.labels = labels
        self.f_score_beta = f_score_beta
        self.average = average

        self.ignore_padding = ignore_padding
        if ignore_padding == True and pad_token_id is None:
            raise ValueError("pad_token_id must be provided if ignore_padding is True")
        self.pad_token_id = pad_token_id

        self.num_matches = 0
        self.num_totals = 0

    def update_step(
        self,
        loss: float,
        y_pred: np.ndarray | Tensor,
        y_true: np.ndarray | Tensor
    ) -> None:
        self.loss += loss
        self.num_batchs += 1


        if isinstance(y_pred, Tensor):
            y_pred = y_pred.cpu().detach().numpy()
        if isinstance(y_true, Tensor):
            y_true = y_true.cpu().detach().numpy()

        self.num_matches += ((y_pred == y_true) & (y_pred != self.pad_token_id)).sum().item()
        self.num_totals += (y_true != self.pad_token_id).sum().item()

        y_pred = y_pred.ravel()
        y_true = y_true.ravel()

        if self.ignore_padding:
            y_pred = y_pred[y_true != self.pad_token_id]
            y_true = y_true[y_true != self.pad_token_id]

        assert y_pred.shape == y_true.shape

        self.pred.append(y_pred)
        self.labels.append(y_true)


    def compute(self) -> dict[str, float]:
        y_pred = np.concatenate(self.pred)
        y_true = np.concatenate(self.labels)

        loss = self.loss / self.num_batchs
        acc = accuracy_score(y_true, y_pred)  # this calculation does not take into account the padding tokens
        precision, recall, f_beta, _ = precision_recall_fscore_support(
            y_true,
            y_pred,
            beta=self.f_score_beta,
            average=self.average
        )
        print(f"{acc = }")
        print(f"{self.num_matches = }")
        print(f"{self.num_totals = }")
        print(f"{self.num_matches / self.num_totals = }")

        return {
            'loss': loss,
            'acc': acc,
            'precision': precision,
            'recall': recall,
            'f_beta': f_beta,
        }

    def report_to_tensorboard(
        self,
        writer: SummaryWriter,
        name: str,
        step: int,
        prefix: str = 'metrics',
    ) -> None:
        scores = self.compute()

        for metric_name, score in scores.items():
            writer.add_scalars(f'{prefix}/{metric_name}', {
                name: score
            }, step)
