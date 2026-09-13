import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase27 1.0
import SPVideoStudio.Commands 1.0
import "theme"
import "components"
import "shortcuts"
ApplicationWindow {
    id: window
    width: 1360; height: 860; minimumWidth: 1080; minimumHeight: 700; visible: false
    title: "MMO Video Studio"; color: Theme.colors.background
    property string currentPage: "home"
    property string selectedWorkflow: "news"
    property string settingsSection: "General"
    property string missingProjectId: ""
    property bool compactNav: width < 1220 || currentPage === "workspace"
    property bool hasOpenProject: currentPage === "workspace" && typeof projectController !== "undefined" && String(projectController.currentProject.id || "").length > 0
    function pageTitle(key) { var names={home:"Home",create:"Create",projects:"Projects",workspace:"Project Workspace",batch:"Batch Factory",voices:"Voices",templates:"Templates",assets:"Assets",models:"Models",settings:"Settings"}; return names[key]||"MMO Video Studio" }
    function pageSource(key) { var sources={home:"pages/HomePage.qml",create:"pages/CreatePage.qml",projects:"pages/ProjectsPage.qml",workspace:"pages/ProjectWorkspacePage.qml",batch:"pages/BatchPage.qml",voices:"pages/VoicesPage.qml",templates:"pages/TemplatesPage.qml",assets:"pages/AssetsPage.qml",models:"pages/ModelsPage.qml",settings:"pages/SettingsPage.qml"}; return Qt.resolvedUrl(sources[key]||sources.home) }
    function navigate(page,context){ currentPage=page; if(page==="settings"){if(context)settingsSection=context}else if(context)selectedWorkflow=context; updateCommandContext() }
    function readinessState(){return typeof readinessController!=="undefined"?readinessController.readiness:({})}
    function applyAccessibilitySettings(){
        if(typeof settingsController!=="undefined")
            Theme.setAccessibility(settingsController.reduceMotionEffective, settingsController.interfaceTextSize, settingsController.strongerFocusIndicator)
    }
    function updateCommandContext(){
        Commands.setProjectOpen(window.hasOpenProject)
        if(!window.hasOpenProject) Commands.setContext("global")
        else if(Commands.context === "global") Commands.setContext("project")
    }
    function dispatchGlobalCommand(commandId){
        if(commandId === "app.save") { Recovery.manualSave(); return true }
        if(commandId === "project.open") { window.navigate("projects", ""); return true }
        if(commandId === "project.new") { window.navigate("create", window.selectedWorkflow); return true }
        if(commandId === "app.settings") { window.navigate("settings", "General"); return true }
        if(commandId === "app.escape") {
            if(commandPalette.opened) { commandPalette.close(); return true }
            if(shortcutSettings.opened) { shortcutSettings.close(); return true }
            if(shortcutHelp.opened) { shortcutHelp.close(); return true }
            if(missingProjectDialog.opened) { missingProjectDialog.close(); return true }
        }
        if(pageLoader.item && typeof pageLoader.item.handleCommand === "function") return pageLoader.item.handleCommand(commandId)
        return false
    }

    ShortcutRouter { window: window }
    CommandPalette { id: commandPalette; parent: Overlay.overlay }
    ShortcutSettings { id: shortcutSettings; parent: Overlay.overlay; onToastRequested:function(message,variant){toast.show(message,variant,2600)} }
    KeyboardShortcutHelp {
        id: shortcutHelp; parent: Overlay.overlay
        onCustomizeRequested: { close(); shortcutSettings.open() }
    }

    Rectangle { anchors.fill:parent; color:Theme.colors.background
        RowLayout { anchors.fill:parent; spacing:0
            Rectangle {
                Layout.preferredWidth: window.compactNav ? 72 : 208; Layout.fillHeight:true; color:Theme.colors.sidebar
                Rectangle { anchors.right:parent.right; width:1; height:parent.height; color:Theme.colors.border }
                ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.sm; spacing:Theme.spacing.xs
                    RowLayout { Layout.fillWidth:true; Layout.preferredHeight:48; spacing:Theme.spacing.sm
                        Rectangle { width:34;height:34;radius:10;color:Theme.colors.accentSoft; Icon{anchors.centerIn:parent;width:18;height:18;name:"spark"} }
                        ColumnLayout { visible:!window.compactNav; Layout.fillWidth:true; spacing:0
                            Text { Layout.fillWidth:true;text:"MMO Video Studio";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodyStrong;font.weight:Theme.type.semibold;elide:Text.ElideRight }
                            Text { text:"Soft Creator Studio";color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption }
                        }
                    }
                    Rectangle {Layout.fillWidth:true;Layout.preferredHeight:1;color:Theme.colors.border;Layout.bottomMargin:Theme.spacing.xs}
                    Repeater { model:[{k:"home",t:"Home",i:"home"},{k:"create",t:"Create",i:"plus-square"},{k:"projects",t:"Projects",i:"projects"},{k:"batch",t:"Batch",i:"batch"},{k:"voices",t:"Voices",i:"mic"},{k:"templates",t:"Templates",i:"template"},{k:"assets",t:"Assets",i:"assets"},{k:"models",t:"Models",i:"models"}]
                        delegate: SidebarItem { required property var modelData; Layout.fillWidth:true; text:window.compactNav?"":modelData.t; accessibleName:modelData.t; iconName:modelData.i; selected:window.currentPage===modelData.k||(modelData.k==="projects"&&window.currentPage==="workspace"); ToolTip.visible:hovered&&window.compactNav;ToolTip.text:modelData.t; onClicked:window.navigate(modelData.k,modelData.k==="create"?window.selectedWorkflow:"") }
                    }
                    Item{Layout.fillHeight:true}
                    Rectangle{Layout.fillWidth:true;Layout.preferredHeight:1;color:Theme.colors.border}
                    SidebarItem {Layout.fillWidth:true;text:window.compactNav?"":"Settings";accessibleName:"Settings";iconName:"settings";selected:window.currentPage==="settings";ToolTip.visible:hovered&&window.compactNav;ToolTip.text:"Settings";onClicked:window.navigate("settings","General")}
                }
            }
            ColumnLayout { Layout.fillWidth:true;Layout.fillHeight:true;spacing:0
                Rectangle { Layout.fillWidth:true;Layout.preferredHeight:56;color:Theme.colors.background
                    Rectangle{anchors.bottom:parent.bottom;width:parent.width;height:1;color:Theme.colors.border}
                    RowLayout { anchors.fill:parent;anchors.leftMargin:Theme.spacing.xlg;anchors.rightMargin:Theme.spacing.xlg;spacing:Theme.spacing.sm
                        IconButton { visible:window.currentPage==="workspace";iconName:"back";tooltip:"Back to Projects";onClicked:window.navigate("projects","") }
                        ColumnLayout {Layout.fillWidth:true;spacing:0
                            Text {Layout.fillWidth:true;text:window.pageTitle(window.currentPage);color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.title;font.weight:Theme.type.semibold;elide:Text.ElideRight}
                            Text {visible:window.currentPage==="workspace";Layout.fillWidth:true;text:window.selectedWorkflow.replace("_"," ");color:Theme.colors.textMuted;font.family:Theme.type.family;font.pixelSize:Theme.type.caption;elide:Text.ElideRight}
                        }
                        SaveStateBadge { visible:window.currentPage==="workspace"; state:Recovery.saveState }
                        StatusBadge { visible:typeof modelController!=="undefined"&&modelController.activeModelId.length>0;text:"Model download";status:"downloading" }
                        StatusBadge { visible:window.width>1260;text:(typeof readinessController!=="undefined"&&readinessController.checking)?"Checking system":(window.readinessState().overallDisplay||"System ready");status:(typeof readinessController!=="undefined"&&readinessController.checking)?"checking":(window.readinessState().overallStatus||"ready") }
                        IconButton { visible:window.currentPage==="settings"; iconName:"settings"; tooltip:"Keyboard Shortcuts · " + Commands.shortcutFor("app.shortcuts"); onClicked:shortcutSettings.open() }
                        IconButton {iconName:"settings";tooltip:"Settings · " + Commands.shortcutFor("app.settings");onClicked:window.navigate("settings","General")}
                    }
                }
                Item {Layout.fillWidth:true;Layout.fillHeight:true
                    Loader {id:pageLoader;anchors.fill:parent;anchors.margins:window.currentPage==="workspace"?Theme.spacing.md:Theme.spacing.xlg;source:window.pageSource(window.currentPage);opacity:status===Loader.Ready?1:0
                        onLoaded:{if(window.currentPage==="create")item.selectedWorkflow=window.selectedWorkflow;if(window.currentPage==="settings")item.section=window.settingsSection;window.updateCommandContext()}
                        Behavior on opacity{NumberAnimation{duration:Theme.animation.normal}}
                    }
                    Connections {target:pageLoader.item;ignoreUnknownSignals:true;function onNavigateRequested(page,workflow){window.navigate(page,workflow)}function onToastRequested(message,variant){toast.show(message,variant,3000)}}
                }
            }
        }
    }
    Component.onCompleted:{if(typeof settingsController!=="undefined"){Theme.setMode(settingsController.theme);applyAccessibilitySettings()} if(typeof projectController!=="undefined")Recovery.setCurrentProject(projectController.currentProject.id||""); updateCommandContext(); window.visible=true}
    onActiveChanged: Commands.setWindowActive(active)
    onHasOpenProjectChanged: updateCommandContext()
    Connections{target:Commands;function onPaletteRequested(){commandPalette.open()}function onShortcutsRequested(){shortcutHelp.open()}function onCommandTriggered(commandId){if(!window.dispatchGlobalCommand(commandId)&&commandId.indexOf("app.")===0)toast.show("That command is not available here.","info",2200)}function onOperationFailed(message){toast.show(message,"error",3600)}}
    Connections{target:typeof settingsController!=="undefined"?settingsController:null;ignoreUnknownSignals:true;function onSettingsChanged(){Theme.setMode(settingsController.theme);window.applyAccessibilitySettings()}function onOperationSucceeded(message){toast.show(message,"success",2600)}function onOperationFailed(message){toast.show(message,"error",4200)}}
    Connections{target:typeof projectController!=="undefined"?projectController:null;ignoreUnknownSignals:true;function onCurrentProjectChanged(){Recovery.setCurrentProject(projectController.currentProject.id||"");window.updateCommandContext()}function onOperationSucceeded(message){toast.show(message,"success",2600)}function onOperationFailed(message){toast.show(message,"error",4200)}function onMissingProjectDetected(projectId){window.missingProjectId=projectId;missingProjectDialog.open()}}
    Connections{target:Recovery;function onOperationSucceeded(message){toast.show(message,"success",2600)}function onOperationFailed(message){toast.show(message,"error",4200)}}
    AppDialog {id:missingProjectDialog;width:Math.min(470,window.width-48);parent:Overlay.overlay;x:(parent.width-width)/2;y:(parent.height-height)/2;header:null;footer:null;closePolicy:Popup.CloseOnEscape
        onOpened: Commands.setModalOpen(true)
        onClosed: Commands.setModalOpen(commandPalette.opened || shortcutSettings.opened || shortcutHelp.opened)
        contentItem:ColumnLayout{spacing:Theme.spacing.lg;Text{text:"Project files could not be found";color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.sectionTitle;font.weight:Theme.type.semibold}Text{Layout.fillWidth:true;text:"The project is still in your library, but its folder is missing. Keep the entry or remove only the library record.";wrapMode:Text.WordWrap;color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall}RowLayout{Layout.fillWidth:true;Item{Layout.fillWidth:true}AppButton{text:"Keep Entry";variant:"secondary";onClicked:missingProjectDialog.close()}AppButton{text:"Remove from Library";variant:"danger";onClicked:{if(typeof projectController!=="undefined"&&projectController.removeFromLibrary(window.missingProjectId))missingProjectDialog.close()}}}}
    }
    Toast{id:toast;anchors.horizontalCenter:parent.horizontalCenter;anchors.bottom:parent.bottom;anchors.bottomMargin:Theme.spacing.xl}
}
