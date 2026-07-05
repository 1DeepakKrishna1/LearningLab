"""app_detector: Naive Bayes application-id detection with risk/action decisioning.

A small, dependency-free package that:
  * generates a master catalog of applications (application_id + categorical features),
  * generates labelled training observations,
  * trains a Categorical Naive Bayes classifier, and
  * predicts the most probable application_id, wrapped in a risk/action decision.
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
