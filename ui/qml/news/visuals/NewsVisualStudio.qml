import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../theme"
import "../../components"
import "../../editor"
Item {
    id: root
    property var controller
    property var sceneController
    function canvasRatio() { var ar=(root.controller && root.controller.currentVisual.layout && root.controller.currentVisual.layout.metadata) ? (root.controller.currentVisual.layout.metadata.aspectRatio||"16:9") : "16:9"; return ar==="9:16"?9/16:(ar==="1:1"?1:16/9) }
    signal toastRequested(string message,string variant)
    signal navigateRequested(string mode)
    Connections { target:root.controller; ignoreUnknownSignals:true; function onOperationFailed(message){root.toastRequested(message,"error")} function onOperationSucceeded(message){root.toastRequested(message,"success")} function onNavigationRequested(mode){root.navigateRequested(mode)} }
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.md
        RowLayout { Layout.fillWidth:true
            ColumnLayout { Layout.fillWidth:true; Text { text:"News Visuals"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.titleLarge; font.weight:Font.DemiBold }; Text { text:"Trusted News data → generic Scene overlays → existing renderer"; color:Theme.colors.textMuted; font.pixelSize:Theme.type.caption } }
            SecondaryButton { text:"Undo"; compact:true; enabled:root.controller && root.controller.canUndo; onClicked:root.controller.undo() }
            SecondaryButton { text:"Redo"; compact:true; enabled:root.controller && root.controller.canRedo; onClicked:root.controller.redo() }
            StatusBadge { text: root.controller ? ((root.controller.readiness.ready||0)+" ready • "+(root.controller.readiness.warnings||0)+" warnings") : "—"; status: root.controller && (root.controller.readiness.errors||0)>0 ? "error" : ((root.controller && (root.controller.readiness.warnings||0)>0)?"warning":"ready") }
            SecondaryButton { text:"Storyboard"; compact:true; onClicked:root.navigateRequested("scenes") }
            SecondaryButton { text:"Timeline"; compact:true; onClicked:root.navigateRequested("timeline") }
            SecondaryButton { text:"Export"; compact:true; onClicked:root.navigateRequested("export") }
        }
        SplitView { Layout.fillWidth:true; Layout.fillHeight:true; orientation: root.width < 1180 ? Qt.Vertical : Qt.Horizontal
            ScrollView { SplitView.preferredWidth:320; SplitView.minimumWidth:260; contentWidth:availableWidth
                ColumnLayout { width:parent.width; spacing:Theme.spacing.sm
                    SectionHeader { title:"Scenes"; subtitle:"Uses the existing Storyboard scene list." }
                    Repeater { model: root.controller ? root.controller.scenes : []
                        Rectangle { Layout.fillWidth:true; Layout.preferredHeight:56; radius:Theme.radius.small; color: root.controller && root.controller.currentSceneId===modelData.id ? Theme.colors.accentSoft : Theme.colors.surfaceHover; border.color:Theme.colors.border
                            MouseArea { anchors.fill:parent; onClicked:root.controller.selectScene(modelData.id) }
                            RowLayout { anchors.fill:parent; anchors.margins:Theme.spacing.sm; Text { Layout.fillWidth:true; text:(modelData.order+1)+". "+modelData.name; color:Theme.colors.textPrimary; elide:Text.ElideRight }; Text { text:(modelData.durationMs/1000).toFixed(1)+"s"; color:Theme.colors.textMuted; font.pixelSize:Theme.type.caption } }
                        }
                    }
                    NewsSceneLayoutPicker { Layout.fillWidth:true; controller:root.controller }
                    NewsThemePanel { Layout.fillWidth:true; controller:root.controller }
                }
            }
            ColumnLayout { SplitView.fillWidth:true; SplitView.preferredWidth:620; spacing:Theme.spacing.sm
                AppCard { Layout.fillWidth:true; Layout.fillHeight:true; color:"#11141B"
                    Item { anchors.fill:parent
                        Rectangle { id:canvas; anchors.centerIn:parent; width:Math.min(parent.width-40,(parent.height-40)*root.canvasRatio()); height:width/root.canvasRatio(); color: root.controller ? (root.controller.theme.backgroundColor||"#0F141A") : "#0F141A"; radius:8; clip:true
                            Repeater { model: root.controller ? root.controller.elements : []
                                delegate: Item { property var ov:modelData.overlay||({}); x:(ov.x||0)*canvas.width; y:(ov.y||0)*canvas.height; width:Math.max(1,(ov.width||.2)*canvas.width); height:Math.max(1,(ov.height||.1)*canvas.height); opacity:ov.opacity===undefined?1:ov.opacity; visible:ov.visible!==false
                                    Rectangle { anchors.fill:parent; visible:ov.type==="shape"; color:ov.style&&ov.style.fillColor?ov.style.fillColor:"#CC20242B"; radius:ov.style&&ov.style.radius?Math.min(ov.style.radius,16):6 }
                                    Column { anchors.centerIn:parent; width:parent.width; visible:ov.type!=="shape" && ov.type!=="logo"; Text { width:parent.width; text:ov.text||""; wrapMode:Text.WordWrap; horizontalAlignment:Text.AlignLeft; color:ov.style&&ov.style.color?ov.style.color:"white"; font.pixelSize:Math.max(11,Math.min(34,(ov.style&&ov.style.fontSize?ov.style.fontSize:42)*canvas.height/1080)); font.bold:(ov.style&&ov.style.fontWeight?ov.style.fontWeight:500)>=700 }; Text { width:parent.width; visible:(ov.secondaryText||"")!==""; text:ov.secondaryText||""; wrapMode:Text.WordWrap; color:"#DDE4EE"; font.pixelSize:Math.max(9,14*canvas.height/1080) } }
                                }
                            }
                            Rectangle { anchors.fill:parent; anchors.margins:Math.min(parent.width,parent.height)*.06; color:"transparent"; border.color:"#44FFFFFF"; border.width:1 }
                        }
                    }
                }
                InfoBanner { Layout.fillWidth:true; variant:"info"; text:"Preview uses the same normalized overlay data as rendering. Font metrics can differ slightly from libass output." }
            }
            ScrollView { SplitView.preferredWidth:360; SplitView.minimumWidth:300; contentWidth:availableWidth
                ColumnLayout { width:parent.width; spacing:Theme.spacing.sm
                    NewsGraphicPicker { Layout.fillWidth:true; controller:root.controller }
                    NewsGraphicInspector { Layout.fillWidth:true; Layout.preferredHeight:360; controller:root.controller }
                }
            }
        }
    }
}
