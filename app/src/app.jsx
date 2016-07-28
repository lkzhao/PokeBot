import React from 'react'
import { render } from 'react-dom'
import { Router, Route, Link, browserHistory, IndexRoute } from 'react-router'


import MapView from './map.jsx';

var App = React.createClass({
  render: function() {
    return <div className="app">
      {this.props.children}
    </div>
  }
});


var Home = React.createClass({
  render: function() {
    var position = {lat:43.4715, lng:-80.5454}
    return <section className="home">
      <MapView initialPosition={position}/>
    </section>
  }
});

    

render((
  <Router history={browserHistory}>
    <Route path="/" component={App}>
      <IndexRoute component={Home} />
    </Route>
  </Router>
), document.getElementById('container'))