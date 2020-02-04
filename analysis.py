import torch
import torchvision
import torch.nn as nn
from thop import profile


def main():
    decomp_type = 'tucker'
    from_epochs = range(0,210,10)
    dataset = 'cifar10'
    arch = 'vgg19'

    for from_epoch in from_epochs:
        before_decomp_record = get_stats_before_decompose(dataset, arch, decomp_type, from_epoch)
        after_decomp_record = get_stats_after_decompose(dataset, arch, decomp_type, from_epoch)
        after_training_decomp_record = get_stats_after_training_decomposed(dataset, arch, decomp_type, from_epoch)

        correlations = [pearsonr(wf.flatten(), wl.flatten()).item() for wf, wl in zip(after_decomp_record['weights'], after_training_decomp_record['weights'])]
        #cosine_similarity = [torch.nn.functional.cosine_similarity(wf.flatten(), wl.flatten()) for wf, wl in zip(after_decomp_record['weights'], after_training_decomp_record['weights'])]
        for wf, wl in zip(after_decomp_record['weights'], after_training_decomp_record['weights']):
            wf.flatten()
            wl.flatten()
            print(torch.nn.functional.cosine_similarity(wf.flatten(), wl.flatten()))

        print("Epoch: ", from_epoch, "\n#params before: ", before_decomp_record['num_params'], "\tafter: ", after_training_decomp_record['num_params'])
        print(cosine_similarity)

def get_params_flops(model, dataset, epochs):
    if dataset == 'cifar10':
        input_size = 1, 3, 32, 32
        num_examples = 50e3
    elif dataset == 'cifar100':
        input_size = 1, 3, 32, 32
        num_examples = 50e3
    elif dataset == 'imagenet':
        input_size = 1, 3, 224, 224
        num_examples = 1.2e6
    else:
        raise Exception('Unhandled dataset: ', dataset)
    
    input = torch.randn(*input_size)
    macs, params = profile(model, inputs=(input, ))

    inference_flops = 2 * macs # two FLOPs per multiply and add
    training_flops = inference_flops * 3 * num_examples * epochs

    return params, inference_flops, training_flops
    

def get_stats_before_decompose(dataset, arch, decomp_type, from_epoch):
    from_epoch_label = '_' + str(from_epoch) if from_epoch < 200 else ''

    model_dir = str('./models/' + dataset + '/' + arch + '/' + 'no_decompose')

    model_file = str(model_dir + '/' + 'model.pth')
    checkpoint_file = str(model_dir + '/' + 'checkpoint' + from_epoch_label + '.pth.tar')
 
    model = torch.load(model_file)
    checkpoint = torch.load(checkpoint_file)
    state_dict = checkpoint['state_dict']
    best_acc = checkpoint['best_acc1']

    #num_params1 = sum(p.numel() for p in state_dict.values()) 
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print("num_params prev: ", num_params)
    print("num_params now: ", num_params)
    num_params, inference_flops, training_flops = get_params_flops(model, dataset, from_epoch - 0)
    weights = get_weights(model)

    return {'num_params': num_params, 'best_acc': best_acc, 'weights': weights}

def get_stats_after_decompose(dataset, arch, decomp_type, from_epoch):
    from_epoch_label = str('from_epoch_' + str(from_epoch) + '_') if from_epoch < 200 else ''

    model_dir = str('./models/' + dataset + '/' + arch + '/' + from_epoch_label + decomp_type + '_decompose')

    model_file = str(model_dir + '/' + 'model.pth')
    #TODO: save checkpoint right after decomposing
    first_epoch = from_epoch + 10
    first_epoch_label = '_' + str(first_epoch) if first_epoch < 200 else ''
    checkpoint_file = str(model_dir + '/' + 'checkpoint' + first_epoch_label + '.pth.tar')

    model = torch.load(model_file)
    checkpoint = torch.load(checkpoint_file)
    state_dict = checkpoint['state_dict']
    best_acc = checkpoint['best_acc1']

    #num_params1 = sum(p.numel() for p in state_dict.values()) 
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    weights = get_weights(model)

    return {'num_params': num_params, 'best_acc': best_acc, 'weights': weights}

def get_stats_after_training_decomposed(dataset, arch, decomp_type, from_epoch):
    from_epoch_label = str('from_epoch_' + str(from_epoch) + '_') if from_epoch < 200 else ''

    model_dir = str('./models/' + dataset + '/' + arch + '/' + from_epoch_label + decomp_type + '_decompose')

    model_file = str(model_dir + '/' + 'model.pth')
    checkpoint_file = str(model_dir + '/' + 'checkpoint.pth.tar')
 
    model = torch.load(model_file)
    checkpoint = torch.load(checkpoint_file)
    state_dict = checkpoint['state_dict']
    best_acc = checkpoint['best_acc1']

    #num_params1 = sum(p.numel() for p in state_dict.values()) 
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    weights = get_weights(model)

    return {'num_params': num_params, 'best_acc': best_acc, 'weights': weights}

def get_weights(model, weights=[]):
    for name, module in model._modules.items():
        if len(list(module.children())) > 0:
            weights = get_weights(module, weights)
        elif type(module) == nn.Conv2d or type(module) == nn.Linear:
            weights.append(module.weight)

    return weights

def pearsonr(x, y):
    mean_x = torch.mean(x)
    mean_y = torch.mean(y)
    xm = x.sub(mean_x)
    ym = y.sub(mean_y)
    r_num = xm.dot(ym)
    r_den = torch.norm(xm, 2) * torch.norm(ym, 2)
    r_val = r_num / r_den
    return r_val

if __name__ == '__main__':
    main()
