# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License").
#   You may not use this file except in compliance with the License.
#   A copy of the License is located at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   or in the "license" file accompanying this file. This file is distributed
#   on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#   express or implied. See the License for the specific language governing
#   permissions and limitations under the License.
# ==============================================================================


from .univariate import UnivariateDistribution
from ...runtime.distributions import SigmoidBernoulliRuntime


class SigmoidBernoulli(UnivariateDistribution):
    """
    The Bernoulli distribution in which the probability of being true is transformed with a Sigmoid function. This is a numerical robust version of Bernoulli distribution where the probability of being true is valid in the real domain.

    :param prob_true: the probability of being true.
    :type prob_true: Variable
    """
    runtime_dist_class = SigmoidBernoulliRuntime

    def __init__(self, prob_true):
        inputs = [('prob_true', prob_true)]
        input_names = ['prob_true']
        output_names = ['random_variable']
        super(SigmoidBernoulli, self).__init__(
            inputs=inputs, outputs=None,
            input_names=input_names,
            output_names=output_names)

    @staticmethod
    def define_variable(prob_true, shape=None):
        """
        Creates and returns a random variable drawn from a Bernoulli distribution.

        :param prob_true: the probability being true.
        :type prob_true: Variable
        :param shape: the shape of the Bernoulli variable.
        :type shape: tuple of int
        :returns: RandomVariable drawn from the Bernoulli distribution.
        :rtypes: Variable
        """
        bernoulli = SigmoidBernoulli(prob_true=prob_true)
        bernoulli._generate_outputs(shape=shape)
        return bernoulli.random_variable