# read commands to be sent to controller
# format:
#   todo: node infos should be collected automatically from containernet
#   add node infos: {cmd:"add_mac", mac:"xx:xx:xx:xx:xx:xx", port:1, node_name:"xyz"}
#   adding a schedule allows to add one or more tuples for a start/ending time of a contact
#   add schedule:   {cmd:"schedule", src:node_name, dst:node_name, [(time:"unix_time",  action:forward/drop)]}



import ast
import json


# ignore empty lines and comments and non dicts
def get_task(task_txt):
    task = {}
    if len(task_txt.strip()) == 0 or task_txt.startswith('#'):
        return
    try:
        task = ast.literal_eval(task_txt)
        if not isinstance(task, dict):
            log.warn("Ignoring non dict instance: {}".format(task_txt))
            return
    except:
        import traceback
        traceback.print_exc()
    return task

def extract_node_infos(task, node_infos):
    if 'cmd' in task and task['cmd'] == 'add_mac':
            node_infos[task['node_name']]={"mac":task['mac'], "port":task['port']}
    return node_infos

# for each line
#   exclude empty lines and proof line for json compatibility
def read_file(fname):
    node_infos = {}
    with open(fname, 'r') as f:
        for l in f:
            task = get_task(l)
            if task is not None:
                node_infos = extract_node_infos(task, node_infos)
    return node_infos

if __name__ == "__main__":
    import sys
    node_infos = read_file("./cmds_test.txt")
    print(node_infos)