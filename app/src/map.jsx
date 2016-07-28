import * as React from 'react';
import $ from "jquery";
import {GoogleMapLoader, GoogleMap, OverlayView} from 'react-google-maps';
import {default as MarkerClusterer} from 'react-google-maps/lib/addons/MarkerClusterer';
import MapStyle from './mapStyle';

import Sidebar from 'react-sidebar';

var ReactToastr = require("react-toastr");
var {ToastContainer} = ReactToastr;
var ToastMessageFactory = React.createFactory(ReactToastr.ToastMessage.animation);

String.prototype.replaceAll = function(search, replacement) {
    var target = this;
    return target.replace(new RegExp(search, 'g'), replacement);
};

class LoginView extends React.Component<any, any> {
  submit(){
    const location = String(this.props.location.lat) + ", " + String(this.props.location.lng)
    this.props.onSubmit({username:this.state.username, password:this.state.password, location:location})
  }
  constructor(props) {
    super(props);
    this.state = {username: '', password: ''};
  }
  handleUChange(event) {
    this.setState({username: event.target.value});
  }
  handlePChange(event) {
    this.setState({password: event.target.value});
  }
  render() {
    return (
      <section className="login">
        <div>
          <h1>Login to PokeBot</h1>
          <div>
            <input type="text" name="username" placeholder="Username or Email" value={this.state.username} onChange={this.handleUChange.bind(this)}/>
            <input type="password" name="password" placeholder="Password" value={this.state.password} onChange={this.handlePChange.bind(this)}/>
            <button onClick={this.submit.bind(this)}>Login</button>
          </div>
        </div>
      </section>
    )
  }
}


export default class MapView extends React.Component<any, any> {
  constructor(props) {
    super(props);
    this.state = { forts:[], position: props.initialPosition, positionRect:{top:0,left:0,right:0,bottom:0}, inventory:[], pokemons:[], range:0 };
  }

  loginSuccess(){
    this.update(() => {
      this.setState({user:true})
      setInterval(()=>{
        this.update()
      }, 2000);
      this.refs.container.success(
        "Login Success!",
        "", {
        timeOut: 3000,
        extendedTimeOut: 1000
      })
      this.gmap.props.map.setCenter(this.state.position)
      this.gmap.props.map.setZoom(17)
    })
  }

  login(data){
    const errorHandler = (e) => {
      this.refs.container.error(
        "Login Failed!",
        "", {
        timeOut: 3000,
        extendedTimeOut: 1000
      })
    }
    $.post("/login", data, (r) => {
      if (r == "ok"){
        this.loginSuccess()
      } else {
        errorHandler()
      }
    }).fail(errorHandler)
  }

  onZoomChanged(){
    const lat = this.gmap.getCenter().lat()
    const zoom = this.gmap.getZoom()
    const rect = this.positionAnchor.getBoundingClientRect()
    const rangePixel = 30 / (156543.03392 * Math.cos(lat * Math.PI / 180) / Math.pow(2, zoom))
    this.setState({range:rangePixel, positionRect:rect})
  }

  update(callback){
    $.getJSON("/updates", (r) => {
      console.log(r)
      const zoom = this.gmap.getZoom()
      const rangePixel = 30 / (156543.03392 * Math.cos(r.position.lat * Math.PI / 180) / Math.pow(2, zoom))
      this.setState({position:r.position,forts:r.forts, inventory:r.inventory, pokemons:r.pokemons, range:rangePixel})
      r.actions.forEach((action, index) =>{
        if (action.action == "catch") {
          if (action.status == "CATCH_SUCCESS") {
            const message = "Catched " + action.name + ", cp " + action.data["cp"]
            this.refs.container.success(
              message,
              "Gotcha!", {
              timeOut: 3000,
              extendedTimeOut: 1000
            })
          } else if (action.status == "CATCH_ESCAPE") {
            const message = action.name + ", cp " + action.data["cp"] + " escaped. "
            this.refs.container.error(
              message,
            "",{
              timeOut: 3000,
              extendedTimeOut: 1000
            })
          } else {
            const message = action.name + ", cp " + action.data["cp"] + ". " + action.status
            this.refs.container.error(
              message,
            "", {
              timeOut: 3000,
              extendedTimeOut: 1000
            })
          }
        } else if (action.action == "encounter") {
          const message = "Encountered " + action.name + ", cp " + action.data["cp"] + ". "
          this.refs.container.success(
            message,
            "", {
            timeOut: 3000,
            extendedTimeOut: 1000
          })
        } else if (action.action == "release") {
          const message = "Released " + action.name + ", cp " + action.cp + ". "
          this.refs.container.success(
            message,
            "", {
            timeOut: 3000,
            extendedTimeOut: 1000
          })
        } else if (action.action == "throw") {
          const message = "Throwed " + action.count + " " + action.name + ". "
          this.refs.container.success(
            message,
            "", {
            timeOut: 3000,
            extendedTimeOut: 1000
          })
        } else if (action.action == "used") {
          const message = "Used " + action.name + ". "
          this.refs.container.success(
            message,
            "", {
            timeOut: 3000,
            extendedTimeOut: 1000
          })
        } else if (action.action == "fortSearch") {
          const message = "Searched PokeStop. "
          if (action.items) {
            this.refs.container.success(
              message,
              "Got" + action.items, {
              timeOut: 3000,
              extendedTimeOut: 1000
            })
          } else {
            this.refs.container.error(
              message,
              action.status, {
              timeOut: 3000,
              extendedTimeOut: 1000
            })
          }
        } else {
          this.refs.container.success(
            action.action,
            "", {
            timeOut: 3000,
            extendedTimeOut: 1000
          })
        }
      })
      if(callback) callback()
    }).fail((e,a,b) => { 
      console.log(e,a,b) 
      if(callback) callback()
    })
  }

  fortClicked(fortId) {
    if (this.state && fortId === this.state.selected) {
      this.setState({selected: undefined});
    } else {
      this.setState({selected: fortId});
    }
  }

  onCenterChanged(){
    const rect = this.positionAnchor.getBoundingClientRect()
    this.setState({positionRect:rect})
  }

  onMapClick(event){
    if (!this.state.user) {
      this.setState({position:{lat:event.latLng.lat(), lng:event.latLng.lng()}}, () => {
        this.onCenterChanged()
      })
    }
  }

  componentDidMount(){
    setTimeout(() => {
      $.get("/login", (r) => {
        if (r=="ok"){
          this.loginSuccess()
        } else {
          this.onCenterChanged()
        }
      })
    }, 1000)
  }

  render() {
    const mcStyles = [{
      height: 26,
      width: 26
    }, {
      height: 30,
      width: 30
    }, {
      height: 34,
      width: 34
    }, {
      height: 38,
      width: 38
    }, {
      height: 42,
      width: 42
    }];
    const style = {"boxShadow": "0 0 20px rgba(0,0,0,0.3), 0 0 0 "+this.state.range+"px rgba(200,212,234,0.3)"}
    var positionView = (
      <OverlayView position={this.state.position} mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}>
        <div ref={(c) => this.positionAnchor = c} className="position"><div className="here" style={style}><div className="inner"/></div></div>
      </OverlayView>
      )
    var markers = []
    for (var key in this.state.forts) {
      const fort = this.state.forts[key]
      const pos = {lat: fort.latitude, lng: fort.longitude};
      let marker;
      if (key === this.state.selected) {
        marker = (
          <div className="marker fort" onClick={this.fortClicked.bind(this, key)}>
            <img src="static/fort.svg" />
          </div>
        );
      } else {
        marker = (
          <div className="marker fort" onClick={this.fortClicked.bind(this, key)}>
            <img src="static/fort.svg" />
          </div>
        );
      }
      markers.push(
        <OverlayView key={key} position={pos} mapPaneName={OverlayView.OVERLAY_MOUSE_TARGET}>
          {marker}
        </OverlayView>
      );
    }

    var markerView = (<MarkerClusterer averageCenter
                      gridSize={ 30 }
                      styles={mcStyles}>
                      {markers}
                    </MarkerClusterer>)

    const map = (<GoogleMap
                  ref={(googleMap) => {this.gmap = googleMap}}
                  defaultZoom={15}
                  onZoomChanged={this.onZoomChanged.bind(this)}
                  onCenterChanged={this.onCenterChanged.bind(this)}
                  options={{styles: MapStyle, disableDefaultUI: true}}
                  defaultCenter={this.state.position}
                  onClick={this.onMapClick.bind(this)}>
                  {positionView}
                  {markerView}
                </GoogleMap>);

    var loginView = ""
    if (!this.state.user) {
      loginView = (<section className="loginContainer marker nohover" style={{top:this.state.positionRect.top, left:this.state.positionRect.left}}>
        <LoginView location={this.state.position} onSubmit={this.login.bind(this)}/>
      </section>)
    }

    var inventory = this.state.inventory.map((item, index) => {
      return (
          <div key={index}>
            <span className="name">{item.name.replace("ITEM_","").replaceAll("_"," ").toLowerCase()}</span><em>{item.count}</em>
          </div>
        )
    })
    var pokemons = []
    this.state.pokemons.forEach((pokes) => {
      for (var key in pokes.data) {
        pokemons.push(
            <div key={key}>
              <span className="name">{pokes.name.toLowerCase()}</span><em>{pokes.data[key]}</em>
            </div>
        )
      }
    })
    var sidebarContent = <div> 
      <h2>Inventory</h2>
      <div>{inventory}</div>
      <h2>Pokemons</h2>
      <div>{pokemons}</div>
    </div>

    return (<div>
      <Sidebar sidebar={sidebarContent}
               docked={this.state.user}
               open={false}
               sidebarClassName="sidebar">
       <div className="MapView">
        <section className="list">
          <GoogleMapLoader
            containerElement={
              <div className="mapContainer" />
            }
            googleMapElement={map}
          />
        </section>
        </div>
      </Sidebar>

      {loginView}
      <ToastContainer ref="container"
                      toastMessageFactory={ToastMessageFactory}
                      className="toast-top-right" />
    </div>);
  }
}

