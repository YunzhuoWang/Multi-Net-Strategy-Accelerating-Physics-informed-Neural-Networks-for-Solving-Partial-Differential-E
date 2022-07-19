import torch
import argparse
import random
import numpy as np
import os
import math
import copy
from torch.utils.data import DataLoader
import torch.nn as nn
from torch import autograd
from torch.autograd import Variable
import time
# class NN(nn.Module):
#     def __init__(self, hidden_dim, input_dim, output_dim, num_layers):
#         super(NN, self).__init__()
#         self.num_layers = num_layers
#         self.output_dim = output_dim
#         self.input_dim = input_dim
#         self.input_layer = nn.Linear(input_dim, hidden_dim)
#         self.middle_layer = nn.Linear(hidden_dim, hidden_dim)
#         self.output_layer = nn.Linear(hidden_dim, output_dim)
#
#     def forward(self, x):
#         out = torch.tanh(self.input_layer(x))
#
#         for i in range(self.num_layers - 2):
#             out = torch.tanh(self.middle_layer(out))
#
#         out = self.output_layer(out)
#         return out

class NN(nn.Module):
    def __init__(self, hidden_dim, input_dim, output_dim, num_layers ):
        super(NN, self).__init__()
        self.output_dim = output_dim
        self.input_dim = input_dim
        # self.devive = device
        self.input_layer = nn.Linear(input_dim, hidden_dim)  # 对输入数据做线性变换，y=Az+b
        self.middle_layer = nn.Sequential()
        for i in range(num_layers - 2):
            self.middle_layer.add_module('hidden_{}'.format(i), nn.Linear(hidden_dim, hidden_dim))
            self.middle_layer.add_module('activation_{}'.format(i), nn.Tanh())
        self.output_layer = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        out = torch.tanh(self.input_layer(x))

        out = self.middle_layer(out)

        out = self.output_layer(out)
        return out

class AVEMSE(nn.Module):
    def __init__(self):
        nn.Module.__init__(self)

    def forward(self, output_Nu,Nu,u,u_t,u_x,u_xxx):
        loss_b = torch.sum(torch.pow(output_Nu-Nu,2))/output_Nu.size()[0]
        a,h,g = 1,6,9.8
        loss_f = torch.sum(torch.pow(u_t+(math.pow(g*h,1/2)+3*math.pow(g*h,1/2)*u/(2*h))*u_x+(h*h*math.pow(g*h,1/2)/6)*u_xxx,2))/u.size()[0]
        loss = loss_b+loss_f
        return loss


def adjust_learning_rate(optimizer, epoch,lr):
    """Sets the learning rate to the initial LR decayed by 10 every 30 epochs"""
    lr = lr * (0.1 ** (epoch // 50))
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr

def reset_random_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
def train(model_0gradient,model_1gradient,model_2gradient,model_tgradient,Nf_dataset,Nu_dataset,loss_fn,device,num_epochs,optimizer,text_x,text_t,text_y):
    inp_x_text = Variable(text_x, requires_grad=False).to(device)
    inp_t_text = Variable(text_t, requires_grad=False).unsqueeze(-1).to(device)
    value_text = Variable(text_y, requires_grad=False).unsqueeze(-1).to(device)
    for epoch_idx in range(num_epochs):
        print(epoch_idx)
        data_loader_Nf = DataLoader(Nf_dataset,num_workers=0, batch_size=14,)
        data_loader_Nu = DataLoader(Nu_dataset,num_workers=0, batch_size=2,)
        for batch_Nf,batch_Nu in zip(data_loader_Nf,data_loader_Nu):
            inp_x_Nf = Variable(batch_Nf[:, 1], requires_grad=True).unsqueeze(-1).to(device)
            inp_t_Nf= Variable(batch_Nf[:, 0], requires_grad=True).unsqueeze(-1).to(device)

            inp_x_Nu = Variable(batch_Nu[:, 1], requires_grad=True).unsqueeze(-1).to(device)
            inp_t_Nu= Variable(batch_Nu[:,  0], requires_grad=True).unsqueeze(-1).to(device)
            value_Nu= Variable(batch_Nu[:,  -1], requires_grad=True).unsqueeze(-1).to(device)
            # o=torch.cat([inp_t_Nf,inp_x_Nf], dim = 1)
            u = model_0gradient (torch.cat([inp_t_Nf,inp_x_Nf], dim = 1)).to(device)
            output_Nu = model_0gradient (torch.cat([inp_t_Nu,inp_x_Nu], dim = 1)).to(device)
            u_x = model_1gradient(torch.cat([inp_t_Nf,inp_x_Nf], dim = 1)).to(device)
            u_xxx = model_2gradient(torch.cat([inp_t_Nf, inp_x_Nf], dim=1)).to(device)
            u_t = model_tgradient(torch.cat([inp_t_Nf, inp_x_Nf], dim=1)).to(device)
            # u_x = autograd.grad(outputs=u, inputs=inp_x_Nf,
            #                     grad_outputs=torch.ones(u.size()).to(device),
            #                     create_graph=True,
            #                     )[0]
            #
            #
            #
            # u_xx = autograd.grad(outputs=u_x, inputs=inp_x_Nf,
            #                     grad_outputs=torch.ones(u_x.size()).to(device),
            #                     create_graph=True,
            #                      )[0]
            #
            # u_t = autograd.grad(outputs=u, inputs=inp_t_Nf,
            #                     grad_outputs=torch.ones(u.size()).to(device),
            #                     create_graph=True,)[0]

            loss = loss_fn(output_Nu,value_Nu,u,u_t,u_x,u_xxx)
            model_0gradient.zero_grad()
            model_1gradient.zero_grad()
            model_2gradient.zero_grad()
            model_tgradient.zero_grad()
            loss.backward()
            optimizer.step()
    with torch.no_grad():
        Inference_time = time.time()
        u_text = model_0gradient(torch.cat([inp_t_text, inp_x_text], dim=1)).to(device)
        Inference_time = time.time()-Inference_time
        loss_text = torch.sum(torch.pow(u_text-value_text,2))/u_text.size()[0]
        print(['training_loss',loss,'text_loss',loss_text])
    loss_=torch.pow(u_text - value_text, 2)
    loss_evermoment = []
    for i in range(100):
        loss_evermoment.append([i*0.01,float(torch.sum(loss_[i*256:(i+1)*256])/256)])
    return loss_evermoment,loss_text,Inference_time,u_text[40*256:41*256],u_text[80*256:81*256]

def Kdv1d_PINN(Nf_dataset, Nu_dataset,text_x,text_t,text_y,num_epochs=100):
    parser = argparse.ArgumentParser()
    parser.add_argument('--gpu', type=int, default=5)
    parser.add_argument('--save_path', type=str, default='')
    parser.add_argument('--load_path', type=str, default='')
    parser.add_argument('--results_path', type=str, default='')
    parser.add_argument('--optimizer', type=str, default='Adam')
    args = parser.parse_args()
    reset_random_seed(42)
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    model_0gradient = NN(20,2,1,20)
    model_1gradient = NN(20,2,1,10)
    model_2gradient = NN(20, 2, 1, 10)
    model_tgradient = NN(20, 2, 1, 10)
    model_0gradient.to(device)
    model_1gradient.to(device)
    model_2gradient.to(device)
    model_tgradient.to(device)
    if args.optimizer =='Adam':
        optimizer = torch.optim.Adam(   [{'params':model_0gradient.parameters(),'lr':1e-2},
                                        {'params': model_1gradient.parameters(), 'lr': 1e-2},
                                        {'params': model_2gradient.parameters(), 'lr': 1e-2},
                                         {'params': model_tgradient.parameters(), 'lr': 1e-2}], lr=0.01,
                                         betas=(0.9, 0.98),weight_decay=1e-4)
    else:
        optimizer = torch.optim.SGD([
            {'params':model_0gradient.parameters(),'lr':1e-2},
            {'params': model_1gradient.parameters(), 'lr': 1e-2},
            {'params': model_2gradient.parameters(), 'lr': 1e-2},
            {'params': model_tgradient.parameters(), 'lr': 1e-2}
        ], lr=1e-2, momentum=0.9)
    # t=optimizer.param_groups
    loss_fn = AVEMSE()
    loss_evermoment,loss_text,Inference_time,value_4,value_8 = train(
        model_0gradient=model_0gradient,
        model_1gradient = model_1gradient,
        model_2gradient = model_2gradient,
        model_tgradient=model_tgradient,
        Nf_dataset=Nf_dataset,
        Nu_dataset=Nu_dataset,
        loss_fn = loss_fn,
        device = device,
        num_epochs = 150,
        optimizer=optimizer,
        text_x = text_x,
        text_t = text_t,
        text_y = text_y
    )
    return loss_evermoment,loss_text,Inference_time,value_4,value_8



