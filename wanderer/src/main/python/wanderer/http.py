'''
Created on 12 Apr 2013

@author: dsnowdon
'''

import BaseHTTPServer

from naoutil.jsonobj import to_json_file
import wanderer

def make_server(env, port):
    server_address = ('', port)
    httpd = NaoHTTPServer(env, server_address, NaoRequestHandler)
    return httpd

def start_server(httpd):
    httpd.serve_forever()

def stop_server(httpd):
    httpd.shutdown()


class NaoHTTPServer(BaseHTTPServer.HTTPServer):
    def __init__(self, env_, serverAddress, requestClass):
        # HTTPServer is not a new style class
        BaseHTTPServer.HTTPServer.__init__(self, serverAddress, requestClass)
        self.env = env_
    
    def get_mapper(self):
        return wanderer.get_mapper_instance(self.env)
    
    def get_data(self, key):
        return self.env.memory.getData(key)
    
    def localized_text(self, basename, propertyName):
        return self.env.localized_text(basename, propertyName)


class NaoRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def get_env(self):
        return self.server.env
    
    def do_GET(self):
        self.server.env.log("REQUEST: "+self.path)
        # list of possible actions, need to have longest paths first for matching to wotk
        responses = [
                     ('/actions/done' , self.do_actions_done),
                     ('actions/planned' , self.do_actions_planned),
                     ('/actions/current' , self.do_actions_current),
                     ('/action' , ['done', 'planned', 'current']),
                     ('/raw/sensed' , self.do_raw_sensed),
                     ('/raw' , ['sensed']),
                     ('/map/json' , self.do_map_json),
                     ('/map/image' , self.do_map_image),
                     ('/map' , ['json', 'image']),
                     ('/' , ['actions','raw','map'])
                     ]
        
        rq = self.path.lower()
        requestCompleted = False
        for prefix, action in responses:
            if rq.startswith(prefix):
                # is action to take a function or literal
                if hasattr(action, '__call__'):
                    params = rq[len(prefix):]
                    action(params)
                else:
                    self.json_response(action)
                requestCompleted = True
                break
        if not requestCompleted:
            self.do_default()

    def json_header(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def json_response(self, obj):
        self.json_header()
        to_json_file(obj, self.wfile)

    def text_response(self, msg):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(msg)

    # return default content
    def do_default(self):
        self.json_response(['actions','raw','map'])
    
    def do_actions_done(self, params):
        obj = wanderer.load_completed_actions(self.get_env())
        self.json_response(obj)
    
    def do_actions_current(self, params):
        obj = wanderer.get_current_action(self.get_env())
        self.json_response(obj)
    
    def do_actions_planned(self, params):
        obj = wanderer.load_plan(self.get_env())
        self.json_response(obj)
    
    def do_raw_sensed(self, params):
        mapper = self.server.get_mapper()
        raw = mapper.get_sensor_data()
        self.json_header()
        self.wfile.write(raw)
    
    def do_map_json(self, params):
        currentMap = self.server.get_mapper().get_map()
        if currentMap:
            self.json_response(currentMap)
        else:
            self.text_response(self.server.localized_text("defaults", "error.unavailable.map.json"))
    
    def do_map_image(self, params):
        self.text_response(self.server.localized_text("defaults", "error.notImplemented.map.image"))
        