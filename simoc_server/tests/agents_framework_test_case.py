import random
import unittest

from simoc_server import db
from simoc_server.agent_model import AgentModel
from simoc_server.agent_model.agents import (BaseAgent, get_agent_by_type_name,
    _add_agent_class_to_mapping)
from simoc_server.agent_model.attribute_meta import AttributeHolder
from simoc_server.database.db_model import AgentType, AgentTypeAttribute
from simoc_server.serialize import AgentDTO
from simoc_server.tests.test_util import setup_db, clear_db

class AgentsFrameworkTestCase(unittest.TestCase):

    """Test the agent framework including attribute inheritance
    and loading of agent type attributes.
    """

    @classmethod
    def setUpClass(cls):
        setup_db()

    @classmethod
    def tearDownClass(cls):
        clear_db()

    def testPersistedAttributes(self):
        # persisted attributes should be saved and loaded to/from the database
        class AgentA(BaseAgent):
            _agent_type_name = "agent_a"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._attr("agent_a_attribute", 16, is_persisted_attr=True)

        # add agent type data to database
        agent_a_type = AgentType(name="agent_a")
        db.session.add(agent_a_type)
        db.session.commit()

        # add agent to agent_name_mappings
        _add_agent_class_to_mapping(AgentA)

        # create agent_model
        agent_model = AgentModel.create_new(100,100)

        # create agent
        agent_a = AgentA(agent_model)

        # make sure attributes are set properly
        self.assertTrue(hasattr(agent_a, "agent_a_attribute"))
        self.assertEqual(agent_a.agent_a_attribute, 16)

        # add agent to model
        agent_model.add_agent(agent_a)

        # snapshot
        snapshot = agent_model.snapshot()
        agent_model_state = snapshot.agent_model_state

        # load model
        loaded_agent_model = AgentModel.load_from_db(agent_model_state)

        # get agents
        loaded_agents = loaded_agent_model.get_agents()
        # make sure agent exists and only exists once
        matching_agents = list(filter(lambda x: x.unique_id == agent_a.unique_id, loaded_agents))
        self.assertTrue(len(matching_agents) == 1)

        # make sure agent attribute loaded correctly
        loaded_agent = matching_agents[0]
        self.assertEqual(loaded_agent.agent_a_attribute, 16)



        ## Repeat above but change value this time
        loaded_agent.agent_a_attribute = 9

        # snapshot
        snapshot_two = loaded_agent_model.snapshot()
        agent_model_state_two = snapshot_two.agent_model_state

        # load model
        loaded_agent_model_two = AgentModel.load_from_db(agent_model_state_two)

        # get agents
        loaded_agents_two = loaded_agent_model_two.get_agents()
        # make sure agent exists and only exists once
        matching_agents_two = list(filter(lambda x: x.unique_id == agent_a.unique_id, loaded_agents_two))
        self.assertTrue(len(matching_agents_two) == 1)

        # make sure agent attribute loaded correctly
        loaded_agent_two = matching_agents_two[0]
        self.assertEqual(loaded_agent_two.agent_a_attribute, 9)

        db.session.delete(snapshot)
        db.session.delete(agent_model_state)
        db.session.delete(snapshot_two)
        db.session.delete(agent_model_state_two)
        db.session.delete(agent_a_type)
        db.session.commit()

    def testPersistedAgentReferences(self):
        # persisted attributes should be saved and loaded to/from the database
        class AgentA(BaseAgent):
            _agent_type_name = "agent_a"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._attr("agent_b_ref", None, _type=AgentB, is_persisted_attr=True)

            def set_agent_b(self, agent_b):
                self.agent_b_ref = agent_b

        class AgentB(BaseAgent):
            _agent_type_name = "agent_b"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._attr("agent_a_ref",  None, _type=AgentA, is_persisted_attr=True)

            def set_agent_a(self, agent_a):
                self.agent_a_ref = agent_a


        # add agent type data to database
        agent_a_type = AgentType(name="agent_a")
        agent_b_type = AgentType(name="agent_b")
        db.session.add(agent_a_type)
        db.session.add(agent_b_type)
        db.session.commit()

        # add agent to agent_name_mappings
        _add_agent_class_to_mapping(AgentA)
        _add_agent_class_to_mapping(AgentB)

        # create agent_model
        agent_model = AgentModel.create_new(100,100)

        # create agent
        agent_a = AgentA(agent_model)
        agent_b = AgentB(agent_model)
        agent_a.set_agent_b(agent_b)
        agent_b.set_agent_a(agent_a)

        # make sure attributes are set properly
        self.assertTrue(hasattr(agent_a, "agent_b_ref"))
        self.assertTrue(hasattr(agent_b, "agent_a_ref"))
        self.assertEqual(agent_a.agent_b_ref, agent_b)
        self.assertEqual(agent_b.agent_a_ref, agent_a)

        # add agents to model
        agent_model.add_agent(agent_a)
        agent_model.add_agent(agent_b)

        # snapshot
        snapshot = agent_model.snapshot()
        agent_model_state = snapshot.agent_model_state

        # load model
        loaded_agent_model = AgentModel.load_from_db(agent_model_state)

        # get agents
        loaded_agents = loaded_agent_model.get_agents()
        # make sure agents exists and only exists once
        matching_agents_a = list(filter(lambda x: x.unique_id == agent_a.unique_id, loaded_agents))
        matching_agents_b = list(filter(lambda x: x.unique_id == agent_b.unique_id, loaded_agents))
        self.assertTrue(len(matching_agents_a) == 1)
        self.assertTrue(len(matching_agents_b) == 1)

        # make sure agent's attribute loaded correctly
        loaded_agent_a = matching_agents_a[0]
        loaded_agent_b = matching_agents_b[0]
        self.assertEqual(loaded_agent_a.agent_b_ref, loaded_agent_b)
        self.assertEqual(loaded_agent_b.agent_a_ref, loaded_agent_a)



        ## Repeat above but change value this time

        agent_a_new = AgentA(loaded_agent_model)
        agent_b_new = AgentB(loaded_agent_model)
        loaded_agent_a.set_agent_b(agent_b_new)
        loaded_agent_b.set_agent_a(agent_a_new)

        # add agents to model
        loaded_agent_model.add_agent(agent_a_new)
        loaded_agent_model.add_agent(agent_b_new)

        # snapshot
        snapshot_two = loaded_agent_model.snapshot()
        agent_model_state_two = snapshot_two.agent_model_state

        # load model
        loaded_agent_model_two = AgentModel.load_from_db(agent_model_state_two)

        # get agents
        loaded_agents_two = loaded_agent_model_two.get_agents()
        print(loaded_agents_two)
        # make sure agent exists and only exists once
        matching_agents_a_two = list(filter(lambda x: x.unique_id == agent_a.unique_id, loaded_agents_two))
        matching_agents_b_two = list(filter(lambda x: x.unique_id == agent_b.unique_id, loaded_agents_two))
        matching_agents_a_new = list(filter(lambda x: x.unique_id == agent_a_new.unique_id, loaded_agents_two))
        matching_agents_b_new = list(filter(lambda x: x.unique_id == agent_b_new.unique_id, loaded_agents_two))

        self.assertTrue(len(matching_agents_a_two) == 1)
        self.assertTrue(len(matching_agents_b_two) == 1)
        self.assertTrue(len(matching_agents_a_new) == 1)
        self.assertTrue(len(matching_agents_b_new) == 1)

        # make sure agent attribute loaded correctly
        loaded_agent_a_two = matching_agents_a_two[0]
        loaded_agent_b_two = matching_agents_b_two[0]
        loaded_agent_a_new = matching_agents_a_new[0]
        loaded_agent_b_new = matching_agents_b_new[0]
        self.assertEqual(loaded_agent_a_two.agent_b_ref, loaded_agent_b_new)
        self.assertEqual(loaded_agent_b_two.agent_a_ref, loaded_agent_a_new)
        self.assertEqual(loaded_agent_a_new.agent_b_ref, None)
        self.assertEqual(loaded_agent_b_new.agent_a_ref, None)

        db.session.delete(snapshot)
        db.session.delete(agent_model_state)
        db.session.delete(snapshot_two)
        db.session.delete(agent_model_state_two)
        db.session.delete(agent_a_type)
        db.session.delete(agent_b_type)
        db.session.commit()


    def testSerializedAgentReferences(self):
        # serialized agents should store unique_id of agent they are referencing in their
        # attributes
        class AgentA(BaseAgent):
            _agent_type_name = "agent_a"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._attr("agent_b_ref", None, _type=AgentB, is_client_attr=True)

            def set_agent_b(self, agent_b):
                self.agent_b_ref = agent_b

        class AgentB(BaseAgent):
            _agent_type_name = "agent_b"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._attr("agent_a_ref",  None, _type=AgentA, is_client_attr=True)

            def set_agent_a(self, agent_a):
                self.agent_a_ref = agent_a


        # add agent type data to database
        agent_a_type = AgentType(name="agent_a")
        agent_b_type = AgentType(name="agent_b")
        db.session.add(agent_a_type)
        db.session.add(agent_b_type)
        db.session.commit()

        # add agent to agent_name_mappings
        _add_agent_class_to_mapping(AgentA)
        _add_agent_class_to_mapping(AgentB)

        # create agent_model
        agent_model = AgentModel.create_new(100,100)

        # create agent
        agent_a = AgentA(agent_model)
        agent_b = AgentB(agent_model)
        agent_a.set_agent_b(agent_b)
        agent_b.set_agent_a(agent_a)

        agent_a_dto = AgentDTO(agent_a)
        agent_b_dto = AgentDTO(agent_b)

        agent_a_state = agent_a_dto.get_state()
        agent_b_state = agent_b_dto.get_state()

        print(agent_a_state)
        self.assertEqual(agent_a_state["attributes"]["agent_b_ref"], agent_b.unique_id)
        self.assertEqual(agent_b_state["attributes"]["agent_a_ref"], agent_a.unique_id)

        db.session.delete(agent_a_type)
        db.session.delete(agent_b_type)
        db.session.commit()

    def testAgentInstanceAttributeCreation(self):
        class AgentParent(BaseAgent):
            _agent_type_name = "agent_parent"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._attr("parent_attribute", 1)

        class AgentMixin(AttributeHolder):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._attr("mixin_attribute", 10)

        class AgentChild(AgentParent, AgentMixin):
            _agent_type_name = "agent_child"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                AgentMixin.__init__(self)
                self._attr("child_attribute", 100)

        agent_parent = AgentType(name="agent_parent")
        agent_child  = AgentType(name="agent_child")

        db.session.add(agent_parent)
        db.session.add(agent_child)
        db.session.commit()

        agent_model = AgentModel.create_new(100, 100)
        agent = AgentChild(agent_model)

        self.assertTrue(hasattr(agent, "parent_attribute"))
        self.assertTrue(hasattr(agent, "mixin_attribute"))
        self.assertTrue(hasattr(agent, "child_attribute"))

        self.assertEqual(agent.parent_attribute, 1)
        self.assertEqual(agent.mixin_attribute, 10)
        self.assertEqual(agent.child_attribute, 100)

        db.session.delete(agent_parent)
        db.session.delete(agent_child)
        db.session.commit()


    def testInheritedAgentTypeAttributes(self):
        # Agent type attributes should be inherited following
        # the same rules as normal python inheritance
        class AgentRoot(BaseAgent):
            _agent_type_name = "agent_root"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

        class AgentParentOne(AgentRoot):
            _agent_type_name = "agent_parent_one"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

        class AgentParentTwo(AgentRoot):
            _agent_type_name = "agent_parent_two"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

        class AgentChildOne(AgentParentOne, AgentParentTwo):
            _agent_type_name = "agent_child_one"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

        class AgentChildTwo(AgentParentTwo, AgentParentOne):
            _agent_type_name = "agent_child_two"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

        # add agent type data to database
        agent_root_type       = AgentType(name="agent_root")
        agent_parent_one_type = AgentType(name="agent_parent_one")
        agent_parent_two_type = AgentType(name="agent_parent_two")
        agent_child_one_type  = AgentType(name="agent_child_one")
        agent_child_two_type  = AgentType(name="agent_child_two")

        # set up agent type attributes
        AgentTypeAttribute(agent_type=agent_root_type,
            name="a", value=10, value_type="int")
        AgentTypeAttribute(agent_type=agent_root_type,
            name="m", value="root_m", value_type="str")

        AgentTypeAttribute(agent_type=agent_parent_one_type,
            name="b", value=11, value_type="int")
        AgentTypeAttribute(agent_type=agent_parent_one_type,
            name="m", value="parent_one_m", value_type="str")
        AgentTypeAttribute(agent_type=agent_parent_one_type,
            name="n", value="parent_one_n", value_type="str")

        AgentTypeAttribute(agent_type=agent_parent_two_type,
            name="c", value=12, value_type="int")
        AgentTypeAttribute(agent_type=agent_parent_two_type,
            name="m", value="parent_two_m", value_type="str")
        AgentTypeAttribute(agent_type=agent_parent_two_type,
            name="o", value="parent_two_o", value_type="str")

        # agent_child_one
        AgentTypeAttribute(agent_type=agent_child_one_type,
            name="d", value=13, value_type="int")
        AgentTypeAttribute(agent_type=agent_child_one_type,
            name="n", value="child_one_n", value_type="str")
        AgentTypeAttribute(agent_type=agent_child_one_type,
            name="p", value="child_one_p", value_type="str")
        
        AgentTypeAttribute(agent_type=agent_child_two_type,
            name="e", value=14, value_type="int")
        AgentTypeAttribute(agent_type=agent_child_two_type,
            name="n", value="child_two_n", value_type="str")
        AgentTypeAttribute(agent_type=agent_child_two_type,
            name="p", value="child_two_p", value_type="str")

        # commit agents
        db.session.add(agent_root_type)
        db.session.add(agent_parent_one_type)
        db.session.add(agent_parent_two_type)
        db.session.add(agent_child_one_type)
        db.session.add(agent_child_two_type)
        db.session.commit()

        # add agents to name mapping
        _add_agent_class_to_mapping(AgentRoot)
        _add_agent_class_to_mapping(AgentParentOne)
        _add_agent_class_to_mapping(AgentParentTwo)
        _add_agent_class_to_mapping(AgentChildOne)
        _add_agent_class_to_mapping(AgentChildTwo)

        agent_model = AgentModel.create_new(100,100)

        # initialize agents in random order
        agents = {}

        constructor_mapping = {
            "root":AgentRoot,
            "parent_one":AgentParentOne,
            "parent_two":AgentParentTwo,
            "child_one":AgentChildOne,
            "child_two":AgentChildTwo,
        }

        keys = list(constructor_mapping.keys())
        random.shuffle(keys)

        for agent_key in keys:
            agents[agent_key] = constructor_mapping[agent_key](agent_model)

        root = agents["root"]
        parent_one = agents["parent_one"]
        parent_two = agents["parent_two"]
        child_one = agents["child_one"]
        child_two = agents["child_two"]

        # get attributes 
        root_a = root.get_agent_type_attribute("a")
        root_m = root.get_agent_type_attribute("m")

        parent_one_a = parent_one.get_agent_type_attribute("a")
        parent_one_b = parent_one.get_agent_type_attribute("b")
        parent_one_m = parent_one.get_agent_type_attribute("m")
        parent_one_n = parent_one.get_agent_type_attribute("n")

        parent_two_a = parent_two.get_agent_type_attribute("a")
        parent_two_c = parent_two.get_agent_type_attribute("c")
        parent_two_m = parent_two.get_agent_type_attribute("m")
        parent_two_o = parent_two.get_agent_type_attribute("o")

        child_one_a = child_one.get_agent_type_attribute("a")
        child_one_b = child_one.get_agent_type_attribute("b")
        child_one_c = child_one.get_agent_type_attribute("c")
        child_one_d = child_one.get_agent_type_attribute("d")
        child_one_m = child_one.get_agent_type_attribute("m")
        child_one_n = child_one.get_agent_type_attribute("n")
        child_one_o = child_one.get_agent_type_attribute("o")
        child_one_p = child_one.get_agent_type_attribute("p")

        child_two_a = child_two.get_agent_type_attribute("a")
        child_two_b = child_two.get_agent_type_attribute("b")
        child_two_c = child_two.get_agent_type_attribute("c")
        child_two_e = child_two.get_agent_type_attribute("e")
        child_two_m = child_two.get_agent_type_attribute("m")
        child_two_n = child_two.get_agent_type_attribute("n")
        child_two_o = child_two.get_agent_type_attribute("o")
        child_two_p = child_two.get_agent_type_attribute("p")

        # test attributes
        self.assertEqual(root_a, 10)
        self.assertEqual(root_m, "root_m")

        self.assertEqual(parent_one_a, 10)
        self.assertEqual(parent_one_b, 11)
        self.assertEqual(parent_one_m, "parent_one_m")
        self.assertEqual(parent_one_n, "parent_one_n")

        self.assertEqual(parent_two_a, 10)
        self.assertEqual(parent_two_c, 12)
        self.assertEqual(parent_two_m, "parent_two_m")
        self.assertEqual(parent_two_o, "parent_two_o")

        self.assertEqual(child_one_a, 10)
        self.assertEqual(child_one_b, 11)
        self.assertEqual(child_one_c, 12)
        self.assertEqual(child_one_d, 13)
        self.assertEqual(child_one_m, "parent_one_m")
        self.assertEqual(child_one_n, "child_one_n")
        self.assertEqual(child_one_o, "parent_two_o")
        self.assertEqual(child_one_p, "child_one_p")

        self.assertEqual(child_two_a, 10)
        self.assertEqual(child_two_b, 11)
        self.assertEqual(child_two_c, 12)
        self.assertEqual(child_two_e, 14)
        self.assertEqual(child_two_m, "parent_two_m")
        self.assertEqual(child_two_n, "child_two_n")
        self.assertEqual(child_two_o, "parent_two_o")
        self.assertEqual(child_two_p, "child_two_p")

        # delete agents
        db.session.delete(agent_root_type)
        db.session.delete(agent_parent_one_type)
        db.session.delete(agent_parent_two_type)
        db.session.delete(agent_child_one_type)
        db.session.delete(agent_child_two_type)
        db.session.commit()


if __name__ == "__main__":
    unittest.main()