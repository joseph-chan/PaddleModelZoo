# Copyright (c) 2016 PaddlePaddle Authors. All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

import sys
import gzip

import paddle.v2 as paddle

from vgg_s import VGG_S


def main():
    datadim = 3 * 224 * 224 
    classdim = 102

    # PaddlePaddle init
    paddle.init(use_gpu=True, trainer_count=1, gpu_id = 1)

    image = paddle.layer.data(
        name="image", type=paddle.data_type.dense_vector(datadim))

    # Create optimizer
    momentum_optimizer = paddle.optimizer.Momentum(
        momentum=0.9,
        regularization=paddle.optimizer.L2Regularization(rate=0.0002 * 50),
        learning_rate=0.01 / 50.0,
        learning_rate_decay_a=0.1,
        learning_rate_decay_b=50000 * 50,
        learning_rate_schedule='discexp')

    # Add neural network config
    net = VGG_S(image)

    out = paddle.layer.fc(
        input=net, size=classdim, act=paddle.activation.Softmax())

    lbl = paddle.layer.data(
        name="label", type=paddle.data_type.integer_value(classdim))
    cost = paddle.layer.classification_cost(input=out, label=lbl)

    # Create parameters
    parameters = paddle.parameters.create(cost)
    with gzip.open('Paddle_vgg_s_pretrained.tar.gz', 'r') as f:
        fparameters = paddle.parameters.Parameters.from_tar(f)
    for param_name in fparameters.names():
        if param_name in parameters.names():
            parameters.set(param_name, fparameters.get(param_name))


    # End batch and end pass event handler
    def event_handler(event):
        if isinstance(event, paddle.event.EndIteration):
            if event.batch_id % 100 == 0:
                print "\nPass %d, Batch %d, Cost %f, %s" % (
                    event.pass_id, event.batch_id, event.cost, event.metrics)
            else:
                sys.stdout.write('.')
                sys.stdout.flush()
        if isinstance(event, paddle.event.EndPass):
            # save parameters
            with gzip.open('vggs_params_pass_%d.tar.gz' % event.pass_id, 'w') as f:
                parameters.to_tar(f)

            result = trainer.test(
                reader=paddle.batch(
                    paddle.dataset.flowers.test(), batch_size=128),
                feeding={'image': 0,
                         'label': 1})
            print "\nTest with Pass %d, %s" % (event.pass_id, result.metrics)

    # Create trainer
    trainer = paddle.trainer.SGD(
        cost=cost, parameters=parameters, update_equation=momentum_optimizer)
    trainer.train(
        reader=paddle.batch(
            paddle.reader.shuffle(
                paddle.dataset.flowers.train(), buf_size=50000),
            batch_size=50),
        num_passes=200,
        event_handler=event_handler,
        feeding={'image': 0,
                 'label': 1})


if __name__ == '__main__':
    main()
