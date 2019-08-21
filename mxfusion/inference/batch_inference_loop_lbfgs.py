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

import mxnet as mx


from .grad_loop import GradLoop


class BatchInferenceLoopLBFGS(GradLoop):
    """
    The class for the main loop for gradient-based optimization using L-BFGS. This is useful if the loss function is
    not stochastic
    """
    def run(self, infr_executor, data, param_dict, ctx, optimizer=None, learning_rate=None, max_iter=1000,
            verbose=False, logger=None):
        """

        :param infr_executor: The MXNet function that computes the training objective.
        :type infr_executor: MXNet Gluon Block
        :param data: a list of observed variables
        :type data: [mxnet.ndarray]
        :param param_dict: The MXNet ParameterDict for Gradient-based optimization
        :type param_dict: mxnet.gluon.ParameterDict
        :param ctx: MXNet context
        :type ctx: mxnet.cpu or mxnet.gpu
        :param optimizer: Not used. Optimizer will always be l-bfgs
        :type optimizer: str
        :param learning_rate: Not used
        :param max_iter: the maximum number of iterations of gradient optimization
        :type max_iter: int
        :param verbose: whether to print per-iteration messages.
        :type verbose: boolean
        :param logger: The logger to send logs to
        :type logger: :class:`inference.Logger`
        """

        from scipy.optimize import fmin_l_bfgs_b

        dict_to_array = ParameterToArrayConverter(param_dict)

        # Use current parameter values as initial point for optimizer
        x0 = dict_to_array.extract_parameter_values_as_array()

        # Create function for optimizer that takes in "x" as only argument
        def f_df(x):
            dict_to_array.set_values_from_array(x)
            with mx.autograd.record():
                loss, loss_for_gradient = infr_executor(mx.nd.zeros(1, ctx=ctx), *data)
                loss_for_gradient.backward()
            return loss.asnumpy().astype('float64'), dict_to_array.extract_parameter_gradients_as_array().astype(
                'float64')

        # Run optimization
        x_opt, f_opt, _ = fmin_l_bfgs_b(f_df, x0=x0, maxiter=max_iter, disp=int(verbose))


class ParameterToArrayConverter:
    """
    This class deals with converting between representing the parameter values in one flattened array and a gluon
    `ParameterDict` object.
    """
    def __init__(self, parameter_dict):
        self.parameter_dict = parameter_dict
        self._get_parameter_sizes(parameter_dict)
        self.array_length = self.i_end[-1]

    def _get_parameter_sizes(self, param_dict):
        """
        Stores stuff like shapes of all the parameters so we can flatten them all to one array for scipy and reshape
        them back to the correct shape
        """
        self.i_start = []  # Start index in the array representation of every parameter
        self.i_end = []  # End index in the array representation of every parameter
        self.shapes = []  # Shapes of each parameter in the parameter dict
        self.dtypes = []  # Types of each parameter
        self.contexts = []  # Context for each parameter
        self.names = []  # The key in the parameter dict for each parameter

        i = 0
        for key, val in param_dict.items():
            if val.grad_req == 'null':
                # Parameter has been fixed
                continue

            data = val.data()
            self.i_start.append(i)
            self.i_end.append(i + data.size)

            i += val.data().size
            self.shapes.append(data.shape)
            self.dtypes.append(data.dtype)
            self.contexts.append(data.context)
            self.names.append(key)

    def set_values_from_array(self, x):
        """
        Sets the updated x values in the parameter dictionary

        :param x: The values of the parameter to be set
        :type x: np.array
        """

        if x.shape[0] != self.array_length:
            raise ValueError('Expected array to be of length {} but is actually length {}'.format(
                self.array_length, x.shape[0]))

        for i, key in enumerate(self.names):
            val = self.parameter_dict[key]
            value_to_set_to = mx.nd.reshape(mx.nd.array(x[self.i_start[i]:self.i_end[i]], dtype=self.dtypes[i],
                                                        ctx=self.contexts[i]), self.shapes[i])
            val.set_data(value_to_set_to)

    def extract_parameter_values_as_array(self):
        """
        Extracts the flattened parameter array from the parameter dictionary

        :return: Array of parameter values
        :rtype: MXNet NDArray
        """
        x = mx.nd.zeros(self.array_length)
        for i, key in enumerate(self.names):
            val = self.parameter_dict[key]
            x[self.i_start[i]:self.i_end[i]] = val.data().reshape((-1,))
        return x.asnumpy()

    def extract_parameter_gradients_as_array(self):
        """
        Extracts gradient information from parameter dictionary

        :return: Array of parameter gradients
        :rtype: MXNet NDArray
        """
        x = mx.nd.zeros(self.array_length)
        for i, key in enumerate(self.names):
            val = self.parameter_dict[key]
            x[self.i_start[i]:self.i_end[i]] = val.data().grad.reshape((-1,))
        return x.asnumpy()
